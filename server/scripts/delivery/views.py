"""
Package views
"""

from pathlib import Path

from django.shortcuts import render, redirect

root = Path(__file__).resolve().parent.parent.parent
with open(root / "VERSION") as fp:
    lines = fp.readlines()
SiteVersion = lines[0].strip()
SiteHash = lines[1].strip()


def news(request):
    """

    :param request:
    :return:
    """
    return render(
        request,
        "delivery/news.html",
        {
            "title": "news",
            "page": "news",
            "has_menu": True,
            "has_submenu": False,
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def revisions(request):
    """

    :param request:
    :return:
    """
    return render(
        request,
        "delivery/revisions.html",
        {
            "title": "revisions",
            "page": "revisions",
            "has_menu": True,
            "has_submenu": False,
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def admin(request):
    """

    :param request:
    :return:
    """
    return redirect("a_users")
    # return render(
    #     request,
    #     "delivery/admin.html",
    #     {
    #         "title": "admin",
    #         "page": "admin",
    #         "has_menu": True,
    #         "version": {"number": SiteVersion, "hash": SiteHash},
    #     },
    # )
