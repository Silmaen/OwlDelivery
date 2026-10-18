"""
Sitemap of the public pages.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import BranchEntry, NewsEntry
from .pages_utils import SITE_DOMAIN

PROTOCOL = "https" if SITE_DOMAIN and ":" not in SITE_DOMAIN else None


class StaticPagesSitemap(Sitemap):
    protocol = PROTOCOL

    def items(self):
        return ["index", "presentation", "news", "branches"]

    def location(self, item):
        return reverse(item)


class NewsSitemap(Sitemap):
    protocol = PROTOCOL

    def items(self):
        return NewsEntry.objects.filter(published=True)

    def location(self, item):
        return reverse("news_detail", args=[item.pk])

    def lastmod(self, item):
        return item.date


class BranchSitemap(Sitemap):
    protocol = PROTOCOL

    def items(self):
        return BranchEntry.objects.filter(visible=True)

    def location(self, item):
        return reverse("revisions", args=[item.name])

    def lastmod(self, item):
        return item.date


SITEMAPS = {"pages": StaticPagesSitemap, "news": NewsSitemap, "branches": BranchSitemap}
