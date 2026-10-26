"""
Traffic statistics: the download counter fed by nginx, and the Statistics tab of the admin.
"""

import logging
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .models import RevisionItemEntry
from .models_stats import HIT_DOWNLOAD
from .perms_utils import can_see_admin, can_see_stats_admin
from .stats_utils import STATS_DEFAULT_PERIOD, STATS_PERIODS, STATS_RETENTION_DAYS, get_report, record_hit
from .views import SITE_HASH, SITE_VERSION, STAFF_ACTIVE
from .views_admin import extract_subpages

logger = logging.getLogger(__name__)

PACKAGES_PREFIX = f"{settings.MEDIA_URL}packages/"


def is_resumed(request):
    """
    A range request that does not start at the first byte continues a download already counted.
    """
    ranges = request.META.get("HTTP_RANGE", "")
    return bool(ranges) and not ranges.replace(" ", "").startswith("bytes=0-")


def stats_download(request):
    """
    Count one package download. nginx mirrors here every request of `/media/packages/` (location internal,
    unreachable from outside), the original URI in X-Original-URI; the answer is thrown away by nginx.
    """
    if request.method != "GET" or is_resumed(request):
        return HttpResponse(status=204)
    path = unquote(urlsplit(request.META.get("HTTP_X_ORIGINAL_URI", "")).path)
    if not path.startswith(PACKAGES_PREFIX):
        return HttpResponse(status=204)
    try:
        item = RevisionItemEntry.objects.filter(package=path.removeprefix(settings.MEDIA_URL)).first()
        if item is not None:
            record_hit(request, HIT_DOWNLOAD, path, item)
    except Exception:
        logger.exception("could not record the download of %s", path)
    return HttpResponse(status=204)


def admin_stats(request):
    """
    Page views and downloads over a period, per page, per user, per country and referring site, per package.
    The admins, the service accounts and the robots are left out unless their box is ticked.
    """
    if not can_see_stats_admin(request):
        return redirect("/")
    days = request.GET.get("days", "")
    days = int(days) if days.isdigit() and int(days) in STATS_PERIODS else STATS_DEFAULT_PERIOD
    audience = {name: request.GET.get(name) == "1" for name in ("admins", "services", "automated")}
    return render(
        request,
        "delivery/admin/stats.html",
        {
            "title": "admin",
            "page": "admin",
            "subpage": "stats",
            "subpages": extract_subpages(request),
            "has_menu": True,
            "has_submenu": True,
            "staff_active": STAFF_ACTIVE,
            "is_admin": can_see_admin(request),
            "version": {"number": SITE_VERSION, "hash": SITE_HASH},
            "periods": STATS_PERIODS,
            "days": days,
            "audience": audience,
            "retention_days": STATS_RETENTION_DAYS,
            "report": get_report(days, **audience),
        },
    )
