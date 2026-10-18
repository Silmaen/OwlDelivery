"""
The home and presentation pages.
"""

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from .models_pages import PAGE_HOME, PAGE_PRESENTATION
from .pages_utils import (
    absolute_url,
    build_about,
    build_features,
    build_gallery,
    build_home_download,
    build_home_news,
    build_json_ld,
    build_link_band,
    build_meta,
    build_release,
    build_roadmap,
    build_samples,
    cached_block,
    get_download_url,
    get_github_url,
    get_hero_image,
    get_sections,
    get_site_settings,
    is_preview,
)
from .perms_utils import can_see_admin
from .release_utils import get_latest_docs_url
from .views import SITE_HASH, SITE_VERSION, STAFF_ACTIVE


def page_context(request, page):
    return {
        "page": page,
        "has_menu": True,
        "has_submenu": False,
        "staff_active": STAFF_ACTIVE,
        "is_admin": can_see_admin(request),
        "version": {"number": SITE_VERSION, "hash": SITE_HASH},
    }


def fill_sections(request, page, sections, builders, preview):
    """
    Attach its data to every section; a section whose block is empty or failed is dropped.
    """
    filled = []
    for section in sections:
        builder = builders.get(section["key"])
        if builder is None:
            continue
        section["data"] = cached_block(request, page, section["key"], lambda b=builder, s=section: b(s), preview)
        if section["data"] is not None:
            filled.append(section)
    return filled


def home(request):
    """
    Landing page: name, Discover link, latest release, latest news.
    """
    preview = is_preview(request)
    settings_row = get_site_settings(request)
    builders = {
        "download": lambda section: build_home_download(preview),
        "news": lambda section: build_home_news(settings_row, preview),
    }
    sections = cached_block(request, PAGE_HOME, "sections", lambda: get_sections(PAGE_HOME, preview), preview) or []
    hero = cached_block(
        request, PAGE_HOME, "hero", lambda: {"image": get_hero_image(settings_row, preview)}, preview
    ) or {"image": None}
    hero["discover_url"] = reverse("presentation")
    context = page_context(request, PAGE_HOME)
    context.update(
        {
            "preview": preview,
            "hero": hero,
            "sections": fill_sections(request, PAGE_HOME, sections, builders, preview),
            "meta": build_meta(request, settings_row, reverse("index"), settings_row.site_name),
        }
    )
    return render(request, "delivery/home.html", context)


def build_presentation_hero(settings_row, preview):
    return {
        "image": get_hero_image(settings_row, preview),
        "download_url": get_download_url(),
        "docs_url": get_latest_docs_url(),
        "github_url": get_github_url(),
    }


def presentation(request):
    """
    The full presentation of the engine.
    """
    preview = is_preview(request)
    settings_row = get_site_settings(request)
    builders = {
        "gallery": lambda section: build_gallery(preview),
        "features": lambda section: build_features(preview),
        "release": lambda section: build_release(settings_row, preview),
        "samples": lambda section: build_samples(preview),
        "roadmap": lambda section: build_roadmap(settings_row, preview),
        "about": build_about,
        "links": lambda section: build_link_band(preview),
    }
    sections = (
        cached_block(request, PAGE_PRESENTATION, "sections", lambda: get_sections(PAGE_PRESENTATION, preview), preview)
        or []
    )
    hero = cached_block(
        request, PAGE_PRESENTATION, "hero", lambda: build_presentation_hero(settings_row, preview), preview
    ) or {"image": None}
    sections = fill_sections(request, PAGE_PRESENTATION, sections, builders, preview)
    release = next((section["data"]["release"] for section in sections if section["key"] == "release"), None)
    context = page_context(request, PAGE_PRESENTATION)
    context.update(
        {
            "preview": preview,
            "hero": hero,
            "sections": sections,
            "meta": build_meta(
                request, settings_row, reverse("presentation"), f"Presentation — {settings_row.site_name}"
            ),
            "json_ld": build_json_ld(request, settings_row, release),
        }
    )
    return render(request, "delivery/presentation.html", context)


def robots_txt(request):
    lines = ["User-agent: *", "Allow: /", f"Sitemap: {absolute_url(request, reverse('sitemap'))}"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
