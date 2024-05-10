"""
Package views
"""

from pathlib import Path

from django.shortcuts import render

root = Path(__file__).resolve().parent.parent.parent
with open(root / "VERSION") as fp:
    lines = fp.readlines()
SiteVersion = lines[0].strip()
SiteHash = lines[1].strip()


def index(request):
    """

    :param request:
    :return:
    """
    return render(
        request,
        "index.html",
        {
            "title": "news",
            "page": "news",
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def documentation(request):
    """

    :param request:
    :return:
    """
    return render(
        request,
        "documentation.html",
        {
            "title": "documentation",
            "page": "documentation",
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def download(request):
    """

    :param request:
    :return:
    """
    return render(
        request,
        "download.html",
        {
            "title": "download",
            "page": "download",
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )
