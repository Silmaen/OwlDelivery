"""
Content of the home and presentation pages.

Everything the two pages show is a row of these models: the templates only hold the layout.
"""

import hashlib
from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.images import get_image_dimensions
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import F
from markdownx.models import MarkdownxField
from markdownx.utils import markdownify
from PIL import Image, ImageOps

PAGE_HOME = "home"
PAGE_PRESENTATION = "presentation"
PAGE_CHOICES = ((PAGE_HOME, "Home"), (PAGE_PRESENTATION, "Presentation"))

# The fixed set of sections, in default order. One partial template per pair:
# `delivery/sections/_<page>_<key>.html`.
PAGE_SECTIONS = {
    PAGE_HOME: ("download", "news"),
    PAGE_PRESENTATION: ("gallery", "features", "release", "samples", "roadmap", "about", "links"),
}
SECTION_KEY_CHOICES = tuple((key, key) for keys in PAGE_SECTIONS.values() for key in keys)

STYLE_TAG_CHOICES = (
    ("2d", "2D"),
    ("raycast", "Raycast"),
    ("voxel", "Voxel"),
    ("isometric", "Isometric"),
    ("3d", "3D"),
    ("hud", "HUD"),
    ("editor", "Editor"),
)
STYLE_TAG_ICONS = {
    "2d": "grid_on",
    "raycast": "view_in_ar",
    "voxel": "deployed_code",
    "isometric": "location_city",
    "3d": "view_in_ar",
    "hud": "dashboard",
    "editor": "edit_square",
}
IMAGE_SOURCE_CHOICES = (("admin", "admin"), ("ci", "ci"))
SAMPLE_STATUS_CHOICES = (
    ("planned", "Planned"),
    ("in_progress", "In progress"),
    ("playable", "Playable"),
    ("released", "Released"),
)
MILESTONE_STATUS_CHOICES = (
    ("planned", "Planned"),
    ("in_progress", "In progress"),
    ("released", "Released"),
)
LINK_KIND_CHOICES = (
    ("custom", "Custom"),
    ("github", "GitHub"),
    ("docs_latest", "Latest documentation"),
    ("downloads", "Downloads"),
    ("news", "News"),
    ("changelog", "Changelog"),
    ("roadmap", "Roadmap"),
)
LINK_DERIVED_KINDS = ("docs_latest", "downloads", "news")
LINK_PLACEMENT_CHOICES = (("band", "Link band"), ("footer", "Footer"))

IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "webp"]
IMAGE_MAX_BYTES = 8 * 1024 * 1024
IMAGE_MAX_WIDTH = 3840
THUMBNAIL_WIDTH = 640

DEFAULT_PITCH = (
    "Owl Engine is the C++ engine that mixes rendering styles in one game: 2D, raycast, voxel, isometric and 3D, "
    "stacked under one HUD, in the editor and in game."
)
DEFAULT_META_DESCRIPTION = (
    "Owl Engine: a C++23 game engine and editor mixing 2D, raycast, voxel, isometric and 3D in one game. "
    "Linux and Windows."
)


def render_markdown(text):
    """
    Render a markdown field like the news do.
    :param text: The markdown source.
    :return: Html output.
    """
    return markdownify(str(text or ""))


def validate_showcase_image(value):
    """
    Refuse images that are too heavy or too wide for the pages.
    :param value: The uploaded file.
    """
    if value.size > IMAGE_MAX_BYTES:
        raise ValidationError(f"Image larger than {IMAGE_MAX_BYTES // (1024 * 1024)} MB.")
    width, _ = get_image_dimensions(value)
    if width and width > IMAGE_MAX_WIDTH:
        raise ValidationError(f"Image wider than {IMAGE_MAX_WIDTH} px.")


def file_content_hash(field_file):
    """
    Short content hash of a file, so that its URL changes when the image changes.
    :param field_file: The file to hash.
    :return: 8 hexadecimal characters.
    """
    digest = hashlib.sha256()
    for chunk in field_file.chunks():
        digest.update(chunk)
    field_file.seek(0)
    return digest.hexdigest()[:8]


def showcase_upload_to(instance, filename):
    return f"pages/gallery/{instance.key}-{getattr(instance, '_content_hash', 'raw')}{Path(filename).suffix.lower()}"


class PageContent(models.Model):
    """
    Fields shared by every row of page content.
    """

    published = models.BooleanField(default=True, verbose_name="Published")
    updated = models.DateTimeField(auto_now=True, verbose_name="Last update")

    class Meta:
        abstract = True


class OrderedPageContent(PageContent):
    """
    Page content shown as an ordered list.
    """

    order = models.PositiveIntegerField(default=0, verbose_name="Order")

    class Meta:
        abstract = True
        ordering = ["order", "pk"]


class ShowcaseImage(OrderedPageContent):
    """
    A screenshot, pushed by the engine CI or uploaded in the admin.
    """

    key = models.SlugField(max_length=50, unique=True, verbose_name="Key")
    image = models.ImageField(
        upload_to=showcase_upload_to,
        width_field="width",
        height_field="height",
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS), validate_showcase_image],
        verbose_name="Image",
    )
    thumbnail = models.ImageField(upload_to="pages/thumbs/", blank=True, editable=False)
    width = models.PositiveIntegerField(default=0, editable=False)
    height = models.PositiveIntegerField(default=0, editable=False)
    caption = models.CharField(max_length=160, blank=True, default="", verbose_name="Caption")
    alt_text = models.CharField(max_length=200, verbose_name="Alternative text")
    style_tag = models.CharField(max_length=20, choices=STYLE_TAG_CHOICES, blank=True, default="", verbose_name="Style")
    in_gallery = models.BooleanField(default=True, verbose_name="In the gallery")
    source = models.CharField(max_length=10, choices=IMAGE_SOURCE_CHOICES, default="admin", verbose_name="Source")

    class Meta(OrderedPageContent.Meta):
        verbose_name = "Showcase image"

    def __str__(self):
        return self.key

    def thumbnail_url(self):
        """
        URL of the thumbnail, or of the original when no thumbnail could be made.
        """
        if self.thumbnail:
            return self.thumbnail.url
        return self.image.url if self.image else ""

    def make_thumbnail(self):
        """
        Write the WebP thumbnail beside the original (never wider than `THUMBNAIL_WIDTH`).
        """
        with Image.open(self.image.path) as source:
            picture = ImageOps.exif_transpose(source)
            if picture.width > THUMBNAIL_WIDTH:
                height = max(1, round(picture.height * THUMBNAIL_WIDTH / picture.width))
                picture = picture.resize((THUMBNAIL_WIDTH, height), Image.Resampling.LANCZOS)
            if picture.mode not in ("RGB", "RGBA"):
                picture = picture.convert("RGBA")
            buffer = BytesIO()
            picture.save(buffer, "WEBP", quality=80)
        self.thumbnail.save(f"{Path(self.image.name).stem}.webp", ContentFile(buffer.getvalue()), save=False)

    def save(self, *args, **kwargs):
        new_image = bool(self.image) and not self.image._committed
        previous = None
        if new_image:
            self._content_hash = file_content_hash(self.image)
            if self.pk:
                previous = ShowcaseImage.objects.filter(pk=self.pk).values_list("image", "thumbnail").first()
        super().save(*args, **kwargs)
        if not new_image:
            return
        self.make_thumbnail()
        super().save(update_fields=["thumbnail"])
        for old_name in previous or ():
            if old_name and old_name not in (self.image.name, self.thumbnail.name):
                self.image.storage.delete(old_name)


class SiteSettings(models.Model):
    """
    The site texts and settings: a single row, `pk=1`.
    """

    site_name = models.CharField(max_length=60, default="Owl Engine", verbose_name="Site name")
    tagline = models.CharField(max_length=120, default="One engine, every rendering style", verbose_name="Tagline")
    pitch = MarkdownxField(default=DEFAULT_PITCH, verbose_name="Pitch")
    meta_description = models.CharField(
        max_length=160, default=DEFAULT_META_DESCRIPTION, verbose_name="Meta description"
    )
    hero_image = models.ForeignKey(
        ShowcaseImage, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Hero image"
    )
    social_image = models.ForeignKey(
        ShowcaseImage, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Social image"
    )
    cta_discover_label = models.CharField(
        max_length=40, default="Discover Owl Engine", blank=True, verbose_name="Discover button"
    )
    cta_download_label = models.CharField(max_length=40, default="Download", blank=True, verbose_name="Download button")
    cta_docs_label = models.CharField(
        max_length=40, default="Documentation", blank=True, verbose_name="Documentation button"
    )
    cta_github_label = models.CharField(max_length=40, default="GitHub", blank=True, verbose_name="GitHub button")
    news_count = models.PositiveSmallIntegerField(default=3, verbose_name="News on the home page")
    roadmap_teaser_count = models.PositiveSmallIntegerField(default=2, verbose_name="Planned milestones shown")
    show_dev_build = models.BooleanField(default=True, verbose_name="Show the development build")
    footer_text = models.CharField(
        max_length=200, default="© Argawaen — Owl Engine is MIT licensed.", blank=True, verbose_name="Footer text"
    )
    # Cache key of the pages, bumped by the signals of `delivery.signals` only.
    content_version = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.site_name

    @classmethod
    def load(cls):
        """
        The settings row, created with the defaults on first access.
        """
        settings_row, _ = cls.objects.get_or_create(pk=1)
        return settings_row

    def pitch_md(self):
        return render_markdown(self.pitch)

    def save(self, *args, **kwargs):
        self.pk = 1
        # Never write `content_version` back: an instance loaded before a bump would lower it,
        # and the pages would serve the cache entries of that older version again.
        if not kwargs.get("update_fields") and not kwargs.get("force_insert"):
            if SiteSettings.objects.filter(pk=1).exists():
                kwargs["update_fields"] = [
                    field.name
                    for field in self._meta.concrete_fields
                    if not field.primary_key and field.name != "content_version"
                ]
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("The site settings cannot be deleted.")


def bump_content_version():
    """
    Invalidate the cached blocks of both pages. One SQL update, which fires no signal.
    """
    if not SiteSettings.objects.filter(pk=1).update(content_version=F("content_version") + 1):
        SiteSettings.load()


class PageSection(models.Model):
    """
    Title, intro, visibility and order of one section of a page.
    """

    page = models.CharField(max_length=12, choices=PAGE_CHOICES, verbose_name="Page")
    key = models.CharField(max_length=20, choices=SECTION_KEY_CHOICES, verbose_name="Section")
    title = models.CharField(max_length=80, verbose_name="Title")
    intro = MarkdownxField(blank=True, default="", verbose_name="Intro")
    enabled = models.BooleanField(default=True, verbose_name="Enabled")
    order = models.PositiveIntegerField(default=0, verbose_name="Order")
    updated = models.DateTimeField(auto_now=True, verbose_name="Last update")

    class Meta:
        verbose_name = "Page section"
        unique_together = ("page", "key")
        ordering = ["page", "order", "pk"]

    def __str__(self):
        return f"{self.page}:{self.key}"

    def intro_md(self):
        return render_markdown(self.intro)

    @property
    def published(self):
        return self.enabled


class FeatureCard(OrderedPageContent):
    """
    A "Why Owl Engine" card.
    """

    title = models.CharField(max_length=80, verbose_name="Title")
    icon = models.CharField(max_length=40, blank=True, default="", verbose_name="Icon (Material Symbols name)")
    body = MarkdownxField(verbose_name="Body")
    image = models.ForeignKey(
        ShowcaseImage, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Image"
    )
    link_label = models.CharField(max_length=40, blank=True, default="", verbose_name="Link label")
    link_url = models.URLField(max_length=300, blank=True, default="", verbose_name="Link URL")

    class Meta(OrderedPageContent.Meta):
        verbose_name = "Feature card"

    def __str__(self):
        return self.title

    def body_md(self):
        return render_markdown(self.body)


class SampleGame(OrderedPageContent):
    """
    A sample game made with the engine.
    """

    title = models.CharField(max_length=80, verbose_name="Title")
    slug = models.SlugField(max_length=80, unique=True, verbose_name="Slug")
    inspired_by = models.CharField(max_length=80, blank=True, default="", verbose_name="Inspired by")
    summary = MarkdownxField(verbose_name="Summary")
    exercises = models.CharField(max_length=160, blank=True, default="", verbose_name="Exercises")
    image = models.ForeignKey(
        ShowcaseImage, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="Image"
    )
    link_url = models.URLField(max_length=300, blank=True, default="", verbose_name="Link URL")
    status = models.CharField(max_length=12, choices=SAMPLE_STATUS_CHOICES, default="planned", verbose_name="Status")
    target_version = models.CharField(max_length=20, blank=True, default="", verbose_name="Target version")

    class Meta(OrderedPageContent.Meta):
        verbose_name = "Sample game"

    def __str__(self):
        return self.title

    def summary_md(self):
        return render_markdown(self.summary)

    def status_label(self):
        """
        Badge text: "Planned for v0.5.0", "Playable, ships in v0.4.0", "Released in v0.4.0".
        """
        label = self.get_status_display()
        if not self.target_version:
            return label
        if self.status == "playable":
            return f"{label}, ships in v{self.target_version}"
        if self.status == "released":
            return f"{label} in v{self.target_version}"
        return f"{label} for v{self.target_version}"


class RoadmapMilestone(PageContent):
    """
    A version of the engine roadmap.
    """

    version = models.CharField(max_length=20, unique=True, verbose_name="Version")
    goal = models.CharField(max_length=300, verbose_name="Goal")
    highlights = MarkdownxField(blank=True, default="", verbose_name="Highlights")
    expected_date = models.DateField(null=True, blank=True, verbose_name="Expected date")
    status = models.CharField(max_length=12, choices=MILESTONE_STATUS_CHOICES, default="planned", verbose_name="Status")
    is_target = models.BooleanField(default=False, verbose_name="Long-term target")
    link_url = models.URLField(max_length=300, blank=True, default="", verbose_name="Link URL")

    class Meta:
        verbose_name = "Roadmap milestone"
        ordering = ["version"]

    def __str__(self):
        return self.version

    def highlights_md(self):
        return render_markdown(self.highlights)


class ReleaseNote(PageContent):
    """
    Optional texts added to the derived release of a branch.
    """

    branch = models.CharField(max_length=50, unique=True, verbose_name="Branch")
    title = models.CharField(max_length=120, blank=True, default="", verbose_name="Title")
    release_date = models.DateField(null=True, blank=True, verbose_name="Release date")
    highlights = MarkdownxField(blank=True, default="", verbose_name="Highlights")
    changelog_url = models.URLField(max_length=300, blank=True, default="", verbose_name="Changelog URL")
    news = models.ForeignKey(
        "delivery.NewsEntry",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Announcement",
    )

    class Meta:
        verbose_name = "Release note"
        ordering = ["-branch"]

    def __str__(self):
        return self.branch

    def highlights_md(self):
        return render_markdown(self.highlights)


class SiteLink(OrderedPageContent):
    """
    A link of the presentation link band or of the footer.
    """

    label = models.CharField(max_length=40, verbose_name="Label")
    kind = models.CharField(max_length=12, choices=LINK_KIND_CHOICES, default="custom", verbose_name="Kind")
    url = models.URLField(max_length=300, blank=True, default="", verbose_name="URL")
    icon = models.CharField(max_length=40, blank=True, default="", verbose_name="Icon (Material Symbols name)")
    placement = models.CharField(
        max_length=10, choices=LINK_PLACEMENT_CHOICES, default="band", verbose_name="Placement"
    )

    class Meta(OrderedPageContent.Meta):
        verbose_name = "Site link"

    def __str__(self):
        return self.label

    def clean(self):
        if self.kind not in LINK_DERIVED_KINDS and not self.url:
            raise ValidationError({"url": "A URL is required for this kind of link."})


# Every model of the pages, in the order of the admin blocks.
PAGE_MODELS = (
    SiteSettings,
    PageSection,
    ShowcaseImage,
    FeatureCard,
    SampleGame,
    RoadmapMilestone,
    ReleaseNote,
    SiteLink,
)
