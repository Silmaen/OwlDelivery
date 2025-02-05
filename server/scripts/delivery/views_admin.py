from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.shortcuts import render, redirect

from .Revision_utils import (
    get_revision_branches,
    get_revision_hashes,
    get_revision_info,
    get_all_branches_info,
)
from .db_locking import locker
from .forms import NewsEntryForm, RevisionItemEntryForm, BranchEntryForm
from .models import NewsEntry, NewsComment, RevisionItemEntry, BranchEntry
from .perms_utils import *
from .views import SiteVersion, SiteHash

subpages = [
    {
        "name": "news",
        "url": "a_news",
        "display_name": "News",
        "permission": can_see_news_admin,
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
        "name": "users",
        "url": "a_users",
        "display_name": "Users",
        "permission": can_see_user_admin,
    },
]
staff_active = settings.ENABLE_STAFF
revision_per_page = 15


def extract_subpages(request):
    res = []
    for sub in subpages:
        if sub["permission"](request):
            res.append(sub)
    return res


def admin_users(request):
    """

    :param request:
    :return:
    """
    if not can_see_user_admin(request):
        return redirect("HTTP_REFERER", "/")
    if locker.is_locked():
        return redirect("maintenance")
    entries = User.objects.all()
    p_users = []
    for entry in entries:
        p_users.append(
            {
                "pk": entry.pk,
                "name": entry.username,
                "last_conn": entry.last_login,
                "admin": entry.is_superuser,
                "can_add_news": entry.has_perm("delivery.add_newsentry"),
                "can_delete_news": entry.has_perm("delivery.delete_newsentry"),
                "can_delete_comment": entry.has_perm("delivery.delete_newscomment"),
                "can_add_revision": entry.has_perm("delivery.add_revisionitementry"),
                "can_delete_revision": entry.has_perm(
                    "delivery.delete_revisionitementry"
                ),
                "can_view_user": entry.has_perm("auth.view_user"),
                "can_delete_user": entry.has_perm("auth.delete_user"),
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
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "version": {"number": SiteVersion, "hash": SiteHash},
            "users": p_users,
        },
    )


def admin_modif_user(request, pk):
    """

    :param request:
    :param pk:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect("HTTP_REFERER", "/")
    if not request.user.has_perm("auth.delete_user"):
        return redirect(request.META.get("HTTP_REFERER", "a_news"))
    if locker.is_locked():
        return redirect("maintenance")
    if request.method == "POST":
        user = User.objects.get(pk=pk)
        if "action" not in request.POST:
            return redirect(request.META.get("HTTP_REFERER", "a_users"))
        if request.POST["action"] == "delete":
            user.delete()
        elif request.POST["action"] == "toggle_user_delete":
            ido = Permission.objects.get(codename="delete_user")
            if user.has_perm("auth.delete_user"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST["action"] == "toggle_user_view":
            ido = Permission.objects.get(codename="view_user")
            if user.has_perm("auth.view_user"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST["action"] == "toggle_news_add":
            ido = Permission.objects.get(codename="add_newsentry")
            if user.has_perm("delivery.add_newsentry"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST["action"] == "toggle_news_delete":
            ido = Permission.objects.get(codename="delete_newsentry")
            if user.has_perm("delivery.delete_newsentry"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST["action"] == "toggle_comment_delete":
            ido = Permission.objects.get(codename="delete_newscomment")
            if user.has_perm("delivery.delete_newscomment"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST["action"] == "toggle_revision_add":
            ido = Permission.objects.get(codename="add_revisionitementry")
            if user.has_perm("delivery.add_revisionitementry"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
        elif request.POST["action"] == "toggle_revision_delete":
            ido = Permission.objects.get(codename="delete_revisionitementry")
            if user.has_perm("delivery.delete_revisionitementry"):
                user.user_permissions.remove(ido)
            else:
                user.user_permissions.add(ido)
            user.save()
    return redirect(request.META.get("HTTP_REFERER", "a_users"))


def admin_news(request):
    """

    :param request:
    :return:
    """
    if not can_see_news_admin(request):
        return redirect("HTTP_REFERER", "/")
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
            "staff_active": staff_active,
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def admin_news_detail(request, news_id):
    """
    Page to admin a specific news.
    :param news_id:
    :param request:
    :return:
    """
    news_item = NewsEntry.objects.get(pk=news_id)
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
            "staff_active": staff_active,
            "version": {"number": SiteVersion, "hash": SiteHash},
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
        return redirect("HTTP_REFERER", "/")
    if not request.user.has_perm("delivery.delete_newsentry"):
        return redirect(request.META.get("HTTP_REFERER", "a_news"))
    if request.method == "POST":
        news = NewsEntry.objects.get(pk=news_id)
        if "action" not in request.POST:
            return redirect(request.META.get("HTTP_REFERER", "a_news"))
        if request.POST["action"] == "delete" and request.user.has_perm(
            "delivery.delete_newsentry"
        ):
            news.delete()
    return redirect(request.META.get("HTTP_REFERER", "a_news"))


def admin_modif_comment(request, comment_id):
    """
    Page to process the comment modifications.
    :param request:
    :param comment_id:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect("HTTP_REFERER", "/")
    if not request.user.has_perm("delivery.delete_newscomment"):
        return redirect(request.META.get("HTTP_REFERER", "a_news"))
    if request.method == "POST":
        comment = NewsComment.objects.get(pk=comment_id)
        if "action" not in request.POST:
            return redirect(request.META.get("HTTP_REFERER", "a_news"))
        if request.POST["action"] == "delete" and is_comment_moderator(request):
            comment.delete()
        if request.POST["action"] == "toggle_active" and is_comment_moderator(request):
            comment.active = not comment.active
            comment.save()
    return redirect(request.META.get("HTTP_REFERER", "a_news"))


def admin_revisions_page(request, page):
    if not request.user.is_authenticated:
        return redirect("HTTP_REFERER", "/")
    if not can_see_revision_admin(request):
        return redirect("HTTP_REFERER", "/")
    revisions = {}
    for branch in get_revision_branches():
        revisions[branch] = []
        for rev_hash in get_revision_hashes(branch):
            revisions[branch].append(get_revision_info(rev_hash))
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
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "revisions": revisions,
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def admin_revisions(request):
    """

    :param request:
    :return:
    """
    return admin_revisions_page(request, 0)


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
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "branches": branches,
            "version": {"number": SiteVersion, "hash": SiteHash},
            "debug": add,
        },
    )


def admin_modif_revision(request, rev_hash):
    if not request.user.is_authenticated:
        return redirect("HTTP_REFERER", "/")
    if not request.user.has_perm("delivery.delete_revisionitementry"):
        return redirect(request.META.get("HTTP_REFERER", "a_news"))
    if request.method != "POST":
        return redirect(request.META.get("HTTP_REFERER", "a_news"))
    if "action" not in request.POST:
        return redirect(request.META.get("HTTP_REFERER", "a_news"))
    revs = RevisionItemEntry.objects.filter(hash=rev_hash)
    if request.POST["action"] == "delete" and is_comment_moderator(request):
        for rev in revs:
            rev.delete()
    return redirect(request.META.get("HTTP_REFERER", "a_news"))


def admin_modif_revision_item(request, pk):
    if not request.user.is_authenticated:
        return redirect("HTTP_REFERER", "/")
    if not request.user.has_perm("delivery.delete_revisionitementry"):
        return redirect(request.META.get("HTTP_REFERER", "a_news"))
    if request.method != "POST":
        return redirect(request.META.get("HTTP_REFERER", "a_news"))
    if "action" not in request.POST:
        return redirect(request.META.get("HTTP_REFERER", "a_news"))
    rev_item = RevisionItemEntry.objects.get(pk=pk)
    if request.POST["action"] == "delete" and is_comment_moderator(request):
        rev_item.delete()
    return redirect(request.META.get("HTTP_REFERER", "a_news"))


def admin_edit_revision_item(request, pk):
    rev = RevisionItemEntry.objects.get(pk=pk)
    modified = False
    rev_form = RevisionItemEntryForm(instance=rev)
    if request.method == "POST" and request.user.has_perm(
        "delivery.delete_revisionitementry"
    ):
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
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "revision": rev,
            "rev_form": rev_form,
            "new_revision": modified,
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def admin_revision_detail(request, rev_hash):
    """

    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect("HTTP_REFERER", "/")
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
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )
