from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.paginator import Paginator
from django.db.models import Max, Min
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .db_locking import locker
from .forms import BranchEntryForm, NewsEntryForm, RevisionItemEntryForm
from .models import BranchEntry, NewsComment, NewsEntry, RevisionItemEntry
from .perms_utils import (
    can_see_admin,
    can_see_news_admin,
    can_see_pages_admin,
    can_see_revision_admin,
    can_see_stats_admin,
    can_see_user_admin,
    is_comment_moderator,
)
from .revision_utils import (
    get_all_branches_info,
    get_revision_branches,
    get_revision_info,
)
from .stats_utils import SERVICE_GROUP
from .views import SITE_HASH, SITE_VERSION

SUBPAGES = [
    {
        "name": "news",
        "url": "a_news",
        "display_name": "News",
        "permission": can_see_news_admin,
    },
    {
        "name": "pages",
        "url": "a_pages",
        "display_name": "Pages",
        "permission": can_see_pages_admin,
    },
    {
        "name": "revisions",
        "url": "a_revisions",
        "display_name": "Revisions",
        "permission": can_see_revision_admin,
    },
    {
        "name": "branches",
        "url": "a_branches",
        "display_name": "Branches",
        "permission": can_see_revision_admin,
    },
    {
        "name": "stats",
        "url": "a_stats",
        "display_name": "Statistics",
        "permission": can_see_stats_admin,
    },
    {
        "name": "users",
        "url": "a_users",
        "display_name": "Users",
        "permission": can_see_user_admin,
    },
]
STAFF_ACTIVE = settings.ENABLE_STAFF
REVISION_PER_PAGE = 15
# "Edit pages" toggles every permission on the page models at once.
PAGE_MODEL_NAMES = (
    "sitesettings",
    "pagesection",
    "showcaseimage",
    "featurecard",
    "samplegame",
    "roadmapmilestone",
    "releasenote",
    "sitelink",
)
PAGES_EDIT_CODENAMES = [f"{action}_{model}" for model in PAGE_MODEL_NAMES for action in ("add", "change", "delete")]
# What the engine CI needs to feed the presentation page through the API.
PAGES_PUSH_CODENAMES = ["add_showcaseimage", "add_releasenote"]
# Permission toggles of the users admin: action -> (app label, codenames).
USER_TOGGLES = {
    "toggle_user_delete": ("auth", ["delete_user"]),
    "toggle_user_view": ("auth", ["view_user"]),
    "toggle_news_add": ("delivery", ["add_newsentry"]),
    "toggle_news_delete": ("delivery", ["delete_newsentry"]),
    "toggle_comment_delete": ("delivery", ["delete_newscomment"]),
    "toggle_revision_add": ("delivery", ["add_revisionitementry"]),
    "toggle_revision_delete": ("delivery", ["delete_revisionitementry"]),
    "toggle_pages_edit": ("delivery", PAGES_EDIT_CODENAMES),
    "toggle_pages_push": ("delivery", PAGES_PUSH_CODENAMES),
    "toggle_stats_view": ("delivery", ["view_traffichit"]),
}


def extract_subpages(request):
    res = []
    for sub in SUBPAGES:
        if sub["permission"](request):
            res.append(sub)
    return res


def admin_users(request):
    """

    :param request:
    :return:
    """
    if not can_see_user_admin(request):
        return redirect("/")
    if locker.is_locked():
        return redirect("/")
    entries = User.objects.order_by("username")
    service_ids = set(User.objects.filter(groups__name=SERVICE_GROUP).values_list("pk", flat=True))
    p_users = []
    for entry in entries:
        p_users.append(
            {
                "pk": entry.pk,
                "name": entry.username,
                "manageable": can_manage_user(request, entry),
                "last_conn": entry.last_login,
                "admin": entry.is_superuser,
                "can_add_news": entry.has_perm("delivery.add_newsentry"),
                "can_delete_news": entry.has_perm("delivery.delete_newsentry"),
                "can_delete_comment": entry.has_perm("delivery.delete_newscomment"),
                "can_add_revision": entry.has_perm("delivery.add_revisionitementry"),
                "can_delete_revision": entry.has_perm("delivery.delete_revisionitementry"),
                "can_view_user": entry.has_perm("auth.view_user"),
                "can_delete_user": entry.has_perm("auth.delete_user"),
                "can_edit_pages": all(entry.has_perm(f"delivery.{code}") for code in PAGES_EDIT_CODENAMES),
                "can_push_pages": all(entry.has_perm(f"delivery.{code}") for code in PAGES_PUSH_CODENAMES),
                "can_view_stats": entry.has_perm("delivery.view_traffichit"),
                "is_service": entry.pk in service_ids,
            }
        )
    return render(
        request,
        "delivery/admin/users.html",
        {
            "title": "admin",
            "page": "admin",
            "subpage": "users",
            "subpages": extract_subpages(request),
            "has_menu": True,
            "has_submenu": True,
            "staff_active": STAFF_ACTIVE,
            "is_admin": can_see_admin(request),
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
            "users": p_users,
        },
    )


def can_manage_user(request, target):
    """
    A user manager never changes their own account, and only a superuser changes a superuser.
    """
    if target.pk == request.user.pk:
        return False
    return request.user.is_superuser or not target.is_superuser


def admin_modif_user(request, pk):
    """
    Delete a user or toggle one of their permissions.
    A permission can only be given or taken by someone who holds it: `delete_user` alone grants nothing more.
    :param request:
    :param pk:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect("/")
    if not request.user.has_perm("auth.delete_user"):
        return redirect("a_users")
    if locker.is_locked():
        return redirect("/")
    if request.method != "POST":
        return redirect("a_users")
    user = get_object_or_404(User, pk=pk)
    action = request.POST.get("action", "")
    if not can_manage_user(request, user):
        return redirect("a_users")
    if action == "delete":
        user.delete()
    elif action == "toggle_service":
        # A group rather than a permission: it grants nothing, it only takes the account out of the statistics.
        group, _ = Group.objects.get_or_create(name=SERVICE_GROUP)
        if user.groups.filter(pk=group.pk).exists():
            user.groups.remove(group)
        else:
            user.groups.add(group)
    elif action in USER_TOGGLES:
        app_label, codenames = USER_TOGGLES[action]
        if not all(request.user.has_perm(f"{app_label}.{code}") for code in codenames):
            return redirect("a_users")
        permissions = Permission.objects.filter(content_type__app_label=app_label, codename__in=codenames)
        if all(user.has_perm(f"{app_label}.{code}") for code in codenames):
            user.user_permissions.remove(*permissions)
        else:
            user.user_permissions.add(*permissions)
    return redirect("a_users")


def admin_news(request):
    """

    :param request:
    :return:
    """
    if not can_see_news_admin(request):
        return redirect("/")
    news_list = NewsEntry.objects.order_by("-date")
    modified = False
    if request.method == "POST" and request.user.has_perm("delivery.add_newsentry"):
        news_form = NewsEntryForm(data=request.POST)
        if news_form.is_valid():
            new_news = news_form.save(commit=False)
            new_news.author = request.user
            new_news.save()
            modified = True
    else:
        news_form = NewsEntryForm()
    return render(
        request,
        "delivery/admin/news.html",
        {
            "title": "admin",
            "page": "admin",
            "subpage": "news",
            "subpages": extract_subpages(request),
            "has_menu": True,
            "has_submenu": True,
            "is_admin": can_see_admin(request),
            "news_list": news_list,
            "news_form": news_form,
            "new_news": modified,
            "staff_active": STAFF_ACTIVE,
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
        },
    )


def admin_news_detail(request, news_id):
    """
    Page to admin a specific news.
    :param news_id:
    :param request:
    :return:
    """
    if not can_see_news_admin(request):
        return redirect("/")
    news_item = get_object_or_404(NewsEntry, pk=news_id)
    modified = False
    news_form = NewsEntryForm(instance=news_item)
    if request.method == "POST" and request.user.has_perm("delivery.add_newsentry"):
        news_form = NewsEntryForm(data=request.POST, instance=news_item)
        if news_form.is_valid():
            news_form.save()
            modified = True
    return render(
        request,
        "delivery/admin/news_detail.html",
        {
            "title": "admin",
            "page": "admin",
            "subpage": "news",
            "subpages": extract_subpages(request),
            "has_menu": True,
            "has_submenu": True,
            "is_admin": can_see_admin(request),
            "news_item": news_item,
            "news_form": news_form,
            "new_news": modified,
            "staff_active": STAFF_ACTIVE,
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
        },
    )


def admin_modif_news(request, news_id):
    """
    Page to process the news modifications.
    :param request:
    :param news_id:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST" and request.POST.get("action") == "delete":
        if request.user.has_perm("delivery.delete_newsentry"):
            get_object_or_404(NewsEntry, pk=news_id).delete()
    return redirect("a_news")


def admin_modif_comment(request, comment_id):
    """
    Page to process the comment modifications.
    :param request:
    :param comment_id:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect("/")
    if not is_comment_moderator(request):
        return redirect("a_news")
    comment = get_object_or_404(NewsComment, pk=comment_id)
    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "delete":
            comment.delete()
        elif action == "toggle_active":
            comment.active = not comment.active
            comment.save()
    return redirect("a_news_detail", news_id=comment.related_news_id)


def get_revision_page(page, branch=""):
    """
    One page of the revisions, newest first: one grouped query for the page, then the files of its revisions only.
    :param page: Page number (1-based; out of range gives the nearest page).
    :param branch: Optional branch filter.
    :return: The Django page, its rows carrying the revision info.
    """
    revisions = RevisionItemEntry.objects.values("hash", "branch")
    if branch:
        revisions = revisions.filter(branch=branch)
    revisions = revisions.annotate(built=Min("date"), latest=Max("date")).order_by("-latest", "hash")
    revision_page = Paginator(revisions, REVISION_PER_PAGE).get_page(page)
    revision_page.rows = [{**row, "info": get_revision_info(row["hash"])} for row in revision_page.object_list]
    return revision_page


def revisions_return_url(request):
    """
    Back to the page of the revision admin the action came from (posted `page` and `branch`).
    """
    page = request.POST.get("page", "")
    branch = request.POST.get("branch", "")
    url = reverse("a_revisions_page", args=[int(page)]) if page.isdigit() else reverse("a_revisions")
    if branch in get_revision_branches():
        url += "?" + urlencode({"branch": branch})
    return url


def admin_revisions_page(request, page):
    if not request.user.is_authenticated:
        return redirect("/")
    if not can_see_revision_admin(request):
        return redirect("/")
    branches = get_revision_branches()
    branch = request.GET.get("branch", "")
    if branch not in branches:
        branch = ""
    revision_page = get_revision_page(max(page, 1), branch)
    return render(
        request,
        "delivery/admin/revisions.html",
        {
            "title": "admin",
            "page": "admin",
            "subpage": "revisions",
            "subpages": extract_subpages(request),
            "has_menu": True,
            "has_submenu": True,
            "staff_active": STAFF_ACTIVE,
            "is_admin": can_see_admin(request),
            "revision_page": revision_page,
            "branches": sorted(branches),
            "branch": branch,
            "branch_query": "?" + urlencode({"branch": branch}) if branch else "",
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
        },
    )


def admin_revisions(request):
    """
    First page of the revisions.
    :param request:
    :return:
    """
    return admin_revisions_page(request, 1)


def admin_branches(request):
    if not request.user.is_authenticated:
        return redirect("/")
    if not can_see_revision_admin(request):
        return redirect("/")

    add = ""
    if request.method == "POST":
        if request.user.has_perm("delivery.delete_revisionitementry"):
            data = request.POST.dict()
            add = "No save due to errors"
            if "name" in data.keys():
                branch = BranchEntry.objects.filter(name=data["name"])
                if branch.count() > 0:
                    form_input = BranchEntryForm(request.POST, instance=branch[0])
                    if form_input.is_valid():
                        form_input.save(commit=True)
                        add = "Saved!"
        else:
            add = "Not Authorized to do that!"

    branch_form = get_all_branches_info()
    branches = []
    for b in branch_form:
        branches.append(
            {
                "name": b.name,
                "form": BranchEntryForm(instance=b),
            }
        )
    return render(
        request,
        "delivery/admin/branches.html",
        {
            "title": "admin",
            "page": "admin",
            "subpage": "branches",
            "subpages": extract_subpages(request),
            "has_menu": True,
            "has_submenu": True,
            "staff_active": STAFF_ACTIVE,
            "is_admin": can_see_admin(request),
            "branches": branches,
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
            "debug": add,
        },
    )


def admin_modif_revision(request, rev_hash):
    if not request.user.is_authenticated:
        return redirect("/")
    if not request.user.has_perm("delivery.delete_revisionitementry"):
        return redirect(revisions_return_url(request))
    if request.method == "POST" and request.POST.get("action") == "delete":
        for rev in RevisionItemEntry.objects.filter(hash=rev_hash):
            rev.delete()
    return redirect(revisions_return_url(request))


def admin_modif_revision_item(request, pk):
    if not request.user.is_authenticated:
        return redirect("/")
    if not request.user.has_perm("delivery.delete_revisionitementry"):
        return redirect(revisions_return_url(request))
    if request.method == "POST" and request.POST.get("action") == "delete":
        get_object_or_404(RevisionItemEntry, pk=pk).delete()
    return redirect(revisions_return_url(request))


def admin_edit_revision_item(request, pk):
    if not can_see_revision_admin(request):
        return redirect("/")
    rev = get_object_or_404(RevisionItemEntry, pk=pk)
    modified = False
    rev_form = RevisionItemEntryForm(instance=rev)
    if request.method == "POST" and request.user.has_perm("delivery.delete_revisionitementry"):
        rev_form = RevisionItemEntryForm(data=request.POST, instance=rev)
        if rev_form.is_valid():
            rev_form.save()
            modified = True
    return render(
        request,
        "delivery/admin/revisions_edit.html",
        {
            "title": "admin",
            "page": "admin",
            "subpage": "revisions",
            "subpages": extract_subpages(request),
            "has_menu": True,
            "has_submenu": True,
            "staff_active": STAFF_ACTIVE,
            "is_admin": can_see_admin(request),
            "revision": rev,
            "rev_form": rev_form,
            "new_revision": modified,
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
        },
    )
