from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.shortcuts import render, redirect

from .db_locking import locker
from .forms import NewsEntryForm
from .models import NewsEntry, NewsComment
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
        "name": "users",
        "url": "a_users",
        "display_name": "Users",
        "permission": can_see_user_admin,
    },
]
staff_active = settings.ENABLE_STAFF


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
        return redirect("/")
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
        return redirect("/")
    if not request.user.has_perm("auth.delete_user"):
        return redirect("/")
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
    return redirect(request.META.get("HTTP_REFERER", "a_users"))


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


def admin_revisions(request):
    """

    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect("/")
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
