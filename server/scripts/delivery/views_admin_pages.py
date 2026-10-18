"""
Admin of the home and presentation pages: one generic view pair for every kind of row.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .db_locking import locker
from .forms import (
    FeatureCardForm,
    PageSectionForm,
    ReleaseNoteForm,
    RoadmapMilestoneForm,
    SampleGameForm,
    ShowcaseImageForm,
    SiteLinkForm,
    SiteSettingsForm,
)
from .models_pages import (
    FeatureCard,
    PageSection,
    ReleaseNote,
    RoadmapMilestone,
    SampleGame,
    ShowcaseImage,
    SiteLink,
    SiteSettings,
)
from .perms_utils import can_see_admin, can_see_pages_admin
from .release_utils import parse_version
from .views import SITE_HASH, SITE_VERSION
from .views_admin import STAFF_ACTIVE, extract_subpages

# kind (URL part) -> block of the overview. `ordered`: up / down buttons; `fixed`: rows cannot be added or deleted.
PAGE_KINDS = {
    "section": {"model": PageSection, "form": PageSectionForm, "title": "Sections", "ordered": True, "fixed": True},
    "image": {"model": ShowcaseImage, "form": ShowcaseImageForm, "title": "Gallery", "ordered": True},
    "feature": {"model": FeatureCard, "form": FeatureCardForm, "title": "Features", "ordered": True},
    "sample": {"model": SampleGame, "form": SampleGameForm, "title": "Sample games", "ordered": True},
    "milestone": {"model": RoadmapMilestone, "form": RoadmapMilestoneForm, "title": "Roadmap", "ordered": False},
    "release": {"model": ReleaseNote, "form": ReleaseNoteForm, "title": "Release notes", "ordered": False},
    "link": {"model": SiteLink, "form": SiteLinkForm, "title": "Links", "ordered": True},
}
ROW_ACTIONS = ("delete", "publish", "unpublish", "up", "down")


def get_kind(kind):
    if kind not in PAGE_KINDS:
        raise Http404("Unknown kind of page content.")
    return PAGE_KINDS[kind]


def model_perm(model, action):
    return f"delivery.{action}_{model._meta.model_name}"


def admin_context(request, **extra):
    context = {
        "title": "admin",
        "page": "admin",
        "subpage": "pages",
        "subpages": extract_subpages(request),
        "has_menu": True,
        "has_submenu": True,
        "staff_active": STAFF_ACTIVE,
        "is_admin": can_see_admin(request),
        "version": {"number": SITE_VERSION, "hash": SITE_HASH},
    }
    context.update(extra)
    return context


def describe_row(kind, row):
    """
    Cells of one row of the overview tables.
    """
    if kind == "section":
        title, subtitle = row.title, f"{row.get_page_display()} · {row.key}"
    elif kind == "image":
        title, subtitle = row.key, row.caption
    elif kind == "milestone":
        title, subtitle = f"v{row.version}", row.goal
    elif kind == "release":
        title, subtitle = row.branch, row.title
    elif kind == "link":
        title, subtitle = row.label, f"{row.get_placement_display()} · {row.get_kind_display()}"
    else:
        title, subtitle = row.title, ""
    thumb = ""
    if kind == "image":
        thumb = row.thumbnail_url()
    elif kind in ("sample", "feature") and row.image is not None:
        thumb = row.image.thumbnail_url()
    return {
        "pk": row.pk,
        "title": title,
        "subtitle": subtitle,
        "thumb": thumb,
        "published": row.published,
        "source": getattr(row, "source", ""),
        "updated": row.updated,
    }


def get_rows(kind):
    rows = list(PAGE_KINDS[kind]["model"].objects.all())
    if kind == "milestone":
        rows.sort(key=lambda row: parse_version(row.version) or ())
    return rows


def build_blocks(request, invalid_kind=None, invalid_form=None):
    blocks = []
    for kind, info in PAGE_KINDS.items():
        model = info["model"]
        can_add = not info.get("fixed") and request.user.has_perm(model_perm(model, "add"))
        form = None
        if can_add:
            form = invalid_form if kind == invalid_kind else info["form"]()
        blocks.append(
            {
                "kind": kind,
                "title": info["title"],
                "ordered": info["ordered"],
                "fixed": info.get("fixed", False),
                "rows": [describe_row(kind, row) for row in get_rows(kind)],
                "form": form,
                "open": kind == invalid_kind,
                "can_change": request.user.has_perm(model_perm(model, "change")),
                "can_delete": not info.get("fixed") and request.user.has_perm(model_perm(model, "delete")),
            }
        )
    return blocks


def admin_pages(request):
    """
    Overview of the page content; POST adds a row of the posted `kind`.
    """
    if not can_see_pages_admin(request):
        return redirect("/")
    invalid_kind, invalid_form = None, None
    if request.method == "POST":
        if locker.is_locked():
            return redirect("a_pages")
        kind = request.POST.get("kind", "")
        info = get_kind(kind)
        if info.get("fixed") or not request.user.has_perm(model_perm(info["model"], "add")):
            return redirect("a_pages")
        form = info["form"](data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
            return redirect("a_pages")
        invalid_kind, invalid_form = kind, form
    return render(
        request,
        "delivery/admin/pages.html",
        admin_context(
            request,
            blocks=build_blocks(request, invalid_kind, invalid_form),
            can_change_settings=request.user.has_perm("delivery.change_sitesettings"),
        ),
    )


def admin_pages_detail(request, kind, pk):
    """
    Edit form of one row.
    """
    if not can_see_pages_admin(request):
        return redirect("/")
    info = get_kind(kind)
    row = get_object_or_404(info["model"], pk=pk)
    can_change = request.user.has_perm(model_perm(info["model"], "change"))
    if request.method == "POST" and can_change and not locker.is_locked():
        form = info["form"](data=request.POST, files=request.FILES, instance=row)
        if form.is_valid():
            form.save()
            return redirect("a_pages")
    else:
        form = info["form"](instance=row)
    return render(
        request,
        "delivery/admin/pages_detail.html",
        admin_context(
            request,
            kind=kind,
            kind_title=info["title"],
            row=describe_row(kind, row),
            image=row if kind == "image" else None,
            form=form,
            can_change=can_change,
        ),
    )


def move_row(kind, row, step):
    """
    Swap a row with its neighbour; the rows of its list are renumbered 1..n first, so equal orders still move.
    """
    rows = list(PAGE_KINDS[kind]["model"].objects.all())
    if kind == "section":
        rows = [other for other in rows if other.page == row.page]
    index = next(position for position, other in enumerate(rows) if other.pk == row.pk)
    target = index + step
    if not 0 <= target < len(rows):
        return
    rows[index], rows[target] = rows[target], rows[index]
    for order, other in enumerate(rows, start=1):
        if other.order != order:
            other.order = order
            # save(), not update(): the signals that refresh the cache only see saves.
            other.save(update_fields=["order", "updated"])


def admin_pages_action(request, kind, pk):
    """
    POST only: delete, publish, unpublish, up, down.
    """
    if not can_see_pages_admin(request):
        return redirect("/")
    info = get_kind(kind)
    if request.method != "POST" or locker.is_locked():
        return redirect("a_pages")
    row = get_object_or_404(info["model"], pk=pk)
    action = request.POST.get("action", "")
    if action not in ROW_ACTIONS:
        return redirect("a_pages")
    if action == "delete":
        if not info.get("fixed") and request.user.has_perm(model_perm(info["model"], "delete")):
            row.delete()
        return redirect("a_pages")
    if not request.user.has_perm(model_perm(info["model"], "change")):
        return redirect("a_pages")
    if action in ("publish", "unpublish"):
        field = "enabled" if kind == "section" else "published"
        setattr(row, field, action == "publish")
        row.save(update_fields=[field, "updated"])
    elif info["ordered"]:
        move_row(kind, row, -1 if action == "up" else 1)
    return redirect("a_pages")


def admin_pages_settings(request):
    """
    The site settings form.
    """
    if not can_see_pages_admin(request):
        return redirect("/")
    settings_row = SiteSettings.load()
    can_change = request.user.has_perm("delivery.change_sitesettings")
    if request.method == "POST" and can_change and not locker.is_locked():
        form = SiteSettingsForm(data=request.POST, instance=settings_row)
        if form.is_valid():
            form.save()
            return redirect("a_pages")
    else:
        form = SiteSettingsForm(instance=settings_row)
    return render(
        request,
        "delivery/admin/pages_settings.html",
        admin_context(request, form=form, can_change=can_change),
    )
