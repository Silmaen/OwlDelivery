from django.contrib.auth.models import Permission, User
from django.shortcuts import render, redirect

from .db_locking import locker
from .views import SiteVersion, SiteHash

subpages = [
    {"name": "news", "url": "news", "display_name": "News"},
    {"name": "revisions", "url": "revisions", "display_name": "Revisions"},
    {"name": "users", "url": "a_users", "display_name": "Users"},
]


def users(request):
    """

    :param request:
    :return:
    """
    if not request.user.is_authenticated:
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
                # "can_view_pack": entry.has_perm("pack.view_packageentry"),
                # "can_add_pack": entry.has_perm("pack.add_packageentry"),
                # "can_delete_pack": entry.has_perm("pack.delete_packageentry"),
                "can_view_user": entry.has_perm("auth.view_user"),
                "can_delete_user": entry.has_perm("auth.delete_user"),
            }
        )
    return render(
        request,
        "delivery/users.html",
        {
            "title": "admin",
            "page": "admin",
            "subpage": "users",
            "subpages": subpages,
            "has_menu": True,
            "has_submenu": True,
            "version": {"number": SiteVersion, "hash": SiteHash},
            "users": p_users,
        },
    )


def modif_user(request, pk):
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
            return redirect("users")
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
        # elif request.POST["action"] == "toggle_pack_view":
        #     ido = Permission.objects.get(codename="view_packageentry")
        #     if user.has_perm("pack.view_packageentry"):
        #         user.user_permissions.remove(ido)
        #     else:
        #         user.user_permissions.add(ido)
        #     user.save()
        # elif request.POST["action"] == "toggle_pack_add":
        #     ido = Permission.objects.get(codename="add_packageentry")
        #     if user.has_perm("pack.add_packageentry"):
        #         user.user_permissions.remove(ido)
        #     else:
        #         user.user_permissions.add(ido)
        #     user.save()
        # elif request.POST["action"] == "toggle_pack_delete":
        #     ido = Permission.objects.get(codename="delete_packageentry")
        #     if user.has_perm("pack.delete_packageentry"):
        #         user.user_permissions.remove(ido)
        #     else:
        #         user.user_permissions.add(ido)
        #     user.save()
    return redirect("a_users")
