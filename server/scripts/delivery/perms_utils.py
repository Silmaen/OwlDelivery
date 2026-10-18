"""
Some utility functions for permission management
"""

# Any of these lets a user edit the home and presentation pages.
PAGES_PERMISSIONS = [
    f"delivery.change_{model}"
    for model in (
        "sitesettings",
        "pagesection",
        "showcaseimage",
        "featurecard",
        "samplegame",
        "roadmapmilestone",
        "releasenote",
        "sitelink",
    )
]


def can_see_admin(request):
    if not request.user.is_authenticated:
        return False
    for perm in [
        "auth.view_user",
        "auth.delete_user",
        "delivery.add_newsentry",
        "delivery.delete_newsentry",
        "delivery.delete_newscomment",
        *PAGES_PERMISSIONS,
    ]:
        if request.user.has_perm(perm):
            return True
    return False


def can_see_revision_admin(request):
    if not request.user.is_authenticated:
        return False
    for perm in [
        "delivery.add_revisionitementry",
        "delivery.delete_revisionitementry",
    ]:
        if request.user.has_perm(perm):
            return True
    return False


def can_see_user_admin(request):
    if not request.user.is_authenticated:
        return False
    for perm in [
        "auth.view_user",
        "auth.delete_user",
    ]:
        if request.user.has_perm(perm):
            return True
    return False


def can_see_news_admin(request):
    if not request.user.is_authenticated:
        return False
    for perm in [
        "delivery.add_newsentry",
        "delivery.delete_newsentry",
        "delivery.delete_newscomment",
    ]:
        if request.user.has_perm(perm):
            return True
    return False


def is_comment_moderator(request):
    if not request.user.is_authenticated:
        return False
    for perm in [
        "delivery.delete_newscomment",
    ]:
        if request.user.has_perm(perm):
            return True
    return False


def can_see_pages_admin(request):
    if not request.user.is_authenticated:
        return False
    for perm in PAGES_PERMISSIONS:
        if request.user.has_perm(perm):
            return True
    return False


def can_edit_pages(request):
    return can_see_pages_admin(request)
