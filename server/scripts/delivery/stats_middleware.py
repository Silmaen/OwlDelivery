"""
Records the page views of the public pages.
"""

import logging

from .db_locking import locker
from .models_stats import HIT_PAGE
from .stats_utils import record_hit

logger = logging.getLogger(__name__)

# Not pages a visitor reads: the admin, the API, the account forms, the files nginx serves, the SEO files.
UNTRACKED_PREFIXES = (
    "/admin",
    "/api",
    "/upload",
    "/_stats",
    "/static",
    "/media",
    "/staff",
    "/markdownx",
    "/profile",
    "/script_api",
    "/robots.txt",
    "/sitemap.xml",
)


def is_page_view(request, response):
    return (
        request.method == "GET"
        and response.status_code == 200
        and response.get("Content-Type", "").startswith("text/html")
        and not request.path.startswith(UNTRACKED_PREFIXES)
        and "preview" not in request.GET
    )


class PageViewMiddleware:
    """
    One `TrafficHit` per public page served; a failure to record never breaks the page.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if is_page_view(request, response) and not locker.is_locked():
            try:
                record_hit(request, HIT_PAGE, request.path)
            except Exception:
                logger.exception("could not record the page view of %s", request.path)
        return response
