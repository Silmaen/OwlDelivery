"""
Package views
"""

from pathlib import Path

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404

from .Revision_utils import *
from .forms import NewsCommentForm
from .models import NewsEntry
from .perms_utils import *

root = Path(__file__).resolve().parent.parent.parent
with open(root / "VERSION") as fp:
    lines = fp.readlines()
SiteVersion = lines[0].strip()
SiteHash = lines[1].strip()
staff_active = settings.ENABLE_STAFF


def news(request):
    """
    Main Page, with news.
    :param request: the page request
    :return: the rendered page
    """
    news_list = NewsEntry.objects.order_by("-date")[:15]
    return render(
        request,
        "delivery/news.html",
        {
            "title": "news",
            "page": "news",
            "has_menu": True,
            "has_submenu": False,
            "news_list": news_list,
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def news_details(request, news_id):
    """
    page for one article with details
    :param request: the page request
    :param news_id: the id of the article to find
    :return: the rendered page
    """
    news_item = get_object_or_404(NewsEntry, pk=news_id)
    new_comment = None
    # comment posted (only for authenticated users)
    if request.method == "POST" and request.user.is_authenticated:
        comment_form = NewsCommentForm(data=request.POST)
        if comment_form.is_valid():
            # create an object but don't save to database yet
            new_comment = comment_form.save(commit=False)
            # assign the comment to the current Article
            new_comment.related_news = news_item
            # assign the current user to the comment
            new_comment.author = request.user
            # mark it as active if the user is in Moderators group
            new_comment.active = is_comment_moderator(request)
            # save it to database
            new_comment.save()
    else:
        comment_form = NewsCommentForm()
    return render(
        request,
        "delivery/news_detail.html",
        {
            "title": "news",
            "page": "news",
            "has_menu": True,
            "has_submenu": False,
            "news_item": news_item,
            "comment_form": comment_form,
            "new_comment": new_comment,
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def revisions(request):
    """

    :param request:
    :return:
    """
    current_revision = None
    older_revisions = []
    branch_filter = ""
    # get last hash
    if get_revision_count(branch_filter) > 0:
        hashes = get_revision_hashes(branch_filter)
        current_revision = {
            "hash": hashes[0],
            "date": get_revision_date(hashes[0]),
        }
        for rev_hash in hashes[1:]:
            older_revisions.append(
                {"hash": rev_hash, "date": get_revision_date(rev_hash)}
            )

    return render(
        request,
        "delivery/revisions.html",
        {
            "title": "revisions",
            "page": "revisions",
            "has_menu": True,
            "has_submenu": False,
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "current_revision": current_revision,
            "older_revisions": older_revisions,
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def revision_detail(request, rev_hash):
    """

    :param request:
    :param rev_hash:
    :return:
    """
    current_revision = get_revision_info(rev_hash)

    return render(
        request,
        "delivery/revision_detail.html",
        {
            "title": "revisions",
            "page": "revisions",
            "has_menu": True,
            "has_submenu": False,
            "staff_active": staff_active,
            "is_admin": can_see_admin(request),
            "revision": current_revision,
            "version": {"number": SiteVersion, "hash": SiteHash},
        },
    )


def admin(request):
    """

    :param request:
    :return:
    """
    if not can_see_admin(request):
        return redirect("/")
    if can_see_news_admin(request):
        return redirect("a_news")
    if can_see_revision_admin(request):
        return redirect("a_revisions")
    return redirect("a_users")
