"""
Some utility functions for permission management
"""


def can_see_admin(request):
    if not request.user.is_authenticated:
        return False
    for perm in [
        "auth.view_user",
        "auth.delete_user",
        "delivery.add_newsentry",
        "delivery.delete_newsentry",
        "delivery.delete_newscomment",
    ]:
        if request.user.has_perm(perm):
            return True
    return False


def can_see_revision_admin(request):
    return True


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
