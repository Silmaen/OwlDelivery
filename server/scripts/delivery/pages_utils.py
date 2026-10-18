"""
Helpers to build the home and presentation pages.

Each block of a page is built by one function and cached under `pages:<page>:<block>:<content_version>`:
any change to the rows a page shows bumps `content_version` (see `delivery.signals`), so a worker never serves a
stale block, and the timeout is only a safety net.
"""

import json
import logging
import os

from django.core.cache import cache
from django.db import DatabaseError
from django.templatetags.static import static
from django.urls import reverse

from .models import BranchEntry, NewsEntry
from .models_pages import (
    PAGE_PRESENTATION,
    PAGE_SECTIONS,
    FeatureCard,
    PageSection,
    RoadmapMilestone,
    SampleGame,
    ShowcaseImage,
    SiteLink,
    SiteSettings,
)
from .perms_utils import can_edit_pages
from .release_utils import get_dev_build, get_latest_docs_url, get_latest_release, parse_version

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 600
SITE_DOMAIN = os.environ.get("DOMAIN_NAME", "")
LOGO_STATIC = "img/logo_owl.png"
SAMPLE_PLACEHOLDER_ICON = "sports_esports"


def get_site_settings(request=None):
    """
    The settings row, read once per request.
    :param request: The current request, used as a per-request cache.
    :return: The `SiteSettings` row, or unsaved defaults when the database is unreachable.
    """
    settings_row = getattr(request, "_site_settings", None)
    if settings_row is None:
        try:
            settings_row = SiteSettings.load()
        except DatabaseError:
            settings_row = SiteSettings()
        if request is not None:
            request._site_settings = settings_row
    return settings_row


def is_preview(request):
    """
    `?preview=1` shows the drafts, for a user who can edit the pages only.
    """
    return request.GET.get("preview") == "1" and can_edit_pages(request)


def cached_block(request, page, block, builder, preview=False):
    """
    Build one block of a page, from the cache when possible.
    :param request: The current request.
    :param page: The page name, part of the cache key.
    :param block: The block name, part of the cache key.
    :param builder: Function returning the block data (lists, dicts and rows: nothing lazy).
    :param preview: Preview requests bypass the cache.
    :return: The block data, or None when the block failed (it is then skipped and logged).
    """
    try:
        if preview:
            return builder()
        key = f"pages:{page}:{block}:{get_site_settings(request).content_version}"
        data = cache.get(key)
        if data is None:
            data = builder()
            cache.set(key, data, CACHE_TIMEOUT)
        return data
    except Exception:
        logger.exception("Block %s of page %s failed", block, page)
        return None


def visible(queryset, preview):
    return queryset if preview else queryset.filter(published=True)


def absolute_url(request, path):
    """
    Absolute URL of a path, on `DOMAIN_NAME` when it is set: nginx forwards the host without its port.
    A public domain name is served in https, a `host:port` (local run) in http.
    """
    if SITE_DOMAIN:
        scheme = "http" if ":" in SITE_DOMAIN else "https"
        return f"{scheme}://{SITE_DOMAIN}{path}"
    return request.build_absolute_uri(path)


# --- Shared blocks -----------------------------------------------------------------------------------------------


def get_hero_image(settings_row, preview=False):
    """
    The hero image, else the first gallery image, else None (the template shows the logo).
    """
    image = settings_row.hero_image
    if image is not None and (image.published or preview):
        return image
    return visible(ShowcaseImage.objects.filter(in_gallery=True), preview).first()


def resolve_link(link, docs_url):
    """
    URL of a site link; derived kinds point at the pages of this site.
    :return: A dict for the template, or None when the link resolves to nothing.
    """
    if link.kind == "docs_latest":
        url = docs_url
    elif link.kind == "downloads":
        url = reverse("branches")
    elif link.kind == "news":
        url = reverse("news")
    else:
        url = link.url
    if not url:
        return None
    return {"label": link.label, "url": url, "icon": link.icon, "draft": not link.published}


def get_links(placement, preview=False):
    docs_url = get_latest_docs_url()
    links = (resolve_link(link, docs_url) for link in visible(SiteLink.objects.filter(placement=placement), preview))
    return [link for link in links if link is not None]


def get_github_url():
    link = SiteLink.objects.filter(kind="github", published=True).exclude(url="").first()
    return link.url if link else ""


def get_sections(page, preview=False):
    """
    The sections of a page in their order; disabled ones only in preview, flagged as drafts.
    """
    known = PAGE_SECTIONS[page]
    sections = []
    for section in PageSection.objects.filter(page=page):
        if section.key not in known or not (section.enabled or preview):
            continue
        sections.append(
            {
                "key": section.key,
                "title": section.title,
                "intro_md": section.intro_md(),
                "draft": not section.enabled,
                "template": f"delivery/sections/_{page}_{section.key}.html",
            }
        )
    return sections


def is_section_enabled(page, key):
    return PageSection.objects.filter(page=page, key=key, enabled=True).exists()


def get_download_url():
    """
    Where a Download button leads: the download section of the presentation, or the branch list without it.
    """
    if is_section_enabled(PAGE_PRESENTATION, "release"):
        return reverse("presentation") + "#release"
    return reverse("branches")


# --- Home blocks -------------------------------------------------------------------------------------------------


def build_home_download(preview=False):
    if not BranchEntry.objects.filter(visible=True).exists():
        return None
    return {
        "release": get_latest_release(preview),
        "download_url": get_download_url(),
        "branches_url": reverse("branches"),
    }


def build_home_news(settings_row, preview=False):
    news_list = list(visible(NewsEntry.objects.order_by("-date"), preview)[: settings_row.news_count])
    if not news_list:
        return None
    return {"news_list": news_list, "news_url": reverse("news")}


# --- Presentation blocks -----------------------------------------------------------------------------------------


def build_gallery(preview=False):
    images = list(visible(ShowcaseImage.objects.filter(in_gallery=True), preview))
    return {"images": images} if images else None


def build_features(preview=False):
    cards = list(visible(FeatureCard.objects.select_related("image"), preview))
    return {"cards": cards} if cards else None


def build_release(settings_row, preview=False):
    release = get_latest_release(preview)
    return {
        "release": release,
        "dev_build": get_dev_build(release) if settings_row.show_dev_build else None,
        "github_url": get_github_url(),
    }


def build_samples(preview=False):
    samples = list(visible(SampleGame.objects.select_related("image"), preview))
    if not samples:
        return None
    return {"samples": samples, "placeholder_icon": SAMPLE_PLACEHOLDER_ICON}


def build_roadmap(settings_row, preview=False):
    """
    The current milestone, the next planned ones and the long-term target, in version order.
    """
    milestones = [
        milestone
        for milestone in visible(RoadmapMilestone.objects.exclude(status="released"), preview)
        if parse_version(milestone.version) is not None
    ]
    milestones.sort(key=lambda milestone: parse_version(milestone.version))
    targets = [milestone for milestone in milestones if milestone.is_target]
    steps = [milestone for milestone in milestones if not milestone.is_target]
    if not steps and not targets:
        return None
    current = next((milestone for milestone in steps if milestone.status == "in_progress"), None)
    if current is None and steps:
        current = steps[0]
    shown = []
    if current is not None:
        shown.append(current)
        after = [milestone for milestone in steps if parse_version(milestone.version) > parse_version(current.version)]
        shown += after[: settings_row.roadmap_teaser_count]
    shown += targets[:1]
    link = SiteLink.objects.filter(kind="roadmap", published=True).exclude(url="").first()
    return {"milestones": shown, "current": current, "roadmap_url": link.url if link else ""}


def build_about(section):
    return {} if section["intro_md"].strip() else None


def build_link_band(preview=False):
    links = get_links("band", preview)
    return {"links": links} if links else None


# --- Meta --------------------------------------------------------------------------------------------------------


def build_meta(request, settings_row, path, title):
    """
    OpenGraph and canonical data of a page.
    """
    image = settings_row.social_image
    if image is not None and image.published and image.image:
        og_image = {
            "url": absolute_url(request, image.image.url),
            "width": image.width,
            "height": image.height,
            "alt": image.alt_text,
        }
    else:
        og_image = {"url": absolute_url(request, static(LOGO_STATIC)), "width": 0, "height": 0, "alt": "Owl logo"}
    return {
        "title": title,
        "description": settings_row.meta_description,
        "canonical": absolute_url(request, path),
        "site_name": settings_row.site_name,
        "image": og_image,
    }


def build_json_ld(request, settings_row, release):
    """
    `SoftwareApplication` description of the engine, escaped for a `<script>` element.
    """
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": settings_row.site_name,
        "description": settings_row.meta_description,
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Linux, Windows",
        "license": "https://opensource.org/licenses/MIT",
        "url": absolute_url(request, reverse("presentation")),
    }
    github_url = get_github_url()
    if github_url:
        data["codeRepository"] = github_url
    if release is not None:
        data["softwareVersion"] = release["version"]
        data["downloadUrl"] = absolute_url(request, release["revisions_url"])
    text = json.dumps(data, ensure_ascii=False)
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
