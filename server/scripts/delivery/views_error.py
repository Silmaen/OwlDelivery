"""
Error pages, in the site layout.
"""

from django.shortcuts import render

ERROR_CONTEXT = {"has_menu": True}


def bad_request(request, exception):
    return render(request, "errors/400.html", ERROR_CONTEXT, status=400)


def permission_denied(request, exception):
    return render(request, "errors/403.html", ERROR_CONTEXT, status=403)


def page_not_found(request, exception):
    return render(request, "errors/404.html", ERROR_CONTEXT, status=404)


def server_error(request):
    return render(request, "errors/500.html", ERROR_CONTEXT, status=500)
