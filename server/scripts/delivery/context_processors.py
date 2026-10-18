"""
Template context shared by every page.
"""

from django.urls import reverse

from .pages_utils import cached_block, get_links, get_site_settings
from .perms_utils import can_see_admin
from .release_utils import get_latest_docs_url


def get_nav_entries(request, docs_url):
    """
    Entries of the header navigation; `page` is the value the views pass to mark the active one.
    """
    entries = [
        {"page": "presentation", "label": "Presentation", "icon": "auto_awesome", "url": reverse("presentation")},
        {"page": "news", "label": "News", "icon": "newspaper", "url": reverse("news")},
        {"page": "revisions", "label": "Downloads", "icon": "package_2", "url": reverse("branches")},
    ]
    if docs_url:
        entries.append({"page": "docs", "label": "Docs", "icon": "menu_book", "url": docs_url})
    if can_see_admin(request):
        entries.append({"page": "admin", "label": "Admin", "icon": "admin_panel_settings", "url": reverse("admin")})
    return entries


def site(request):
    """
    The site texts (name, footer, meta description), the navigation and the footer links.
    """
    docs_url = cached_block(request, "site", "docs_url", get_latest_docs_url) or ""
    return {
        "site": get_site_settings(request),
        "nav_entries": get_nav_entries(request, docs_url),
        "footer_links": cached_block(request, "site", "footer_links", lambda: get_links("footer")) or [],
    }
