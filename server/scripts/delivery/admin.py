"""
Administration page
"""

from django.contrib import admin
from django.utils.text import Truncator
from markdownx.admin import MarkdownxModelAdmin

from .models import BranchEntry, NewsComment, NewsEntry, RevisionItemEntry
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

# --------------------- The news -------------------------------------


class NewsEntryAdmin(MarkdownxModelAdmin):
    """
    Admin page for news
    """

    list_display = ("title", "author", "date", "published", "content_overview")
    list_filter = (
        "author",
        "date",
        "published",
    )
    date_hierarchy = "date"
    ordering = ("date",)
    search_fields = ("title", "content")
    prepopulated_fields = {
        "slug": ("title",),
    }
    # Configuration of edit page
    fieldsets = (
        # Fieldset 1 : meta-info (title, author…)
        (
            "General",
            {
                "fields": ("title", "slug", "author", "date", "published"),
            },
        ),
        # Fieldset 2 : article content
        ("Content of the article", {"fields": ("content",)}),
    )

    def save_model(self, request, obj, form, change):
        obj.author = request.user
        super().save_model(request, obj, form, change)

    def content_overview(self, article):
        """
        Get the truncated text.
        """
        return Truncator(article.content).chars(40, truncate="...")

    content_overview.short_description = "content overview"


class NewsCommentAdmin(MarkdownxModelAdmin):
    list_display = ("author", "content", "related_news", "date", "active")
    list_filter = ("author", "date", "active")
    ordering = (
        "related_news",
        "-date",
        "author",
    )
    search_fields = ("author", "content")
    actions = ["approve_comments"]

    def approve_comments(self, request, queryset):
        queryset.update(active=True)

    def save_model(self, request, obj, form, change):
        obj.author = request.user
        super().save_model(request, obj, form, change)


admin.site.register(NewsEntry, NewsEntryAdmin)
admin.site.register(NewsComment, NewsCommentAdmin)


# --------------------- The files -------------------------------------


class RevisionItemEntryAdmin(admin.ModelAdmin):
    """
    Admin model for Revision Items
    """

    list_display = ("hash", "name", "flavor_name", "date", "rev_type")
    list_filter = ("date", "hash")
    ordering = (
        "-date",
        "rev_type",
    )
    # Configuration of edit page
    fieldsets = (
        # Fieldset 1 : meta-info (hash, author…)
        (
            "Name & type",
            {
                "fields": ("name", "rev_type", "flavor_name"),
            },
        ),
        # Fieldset 2 : revision info (title, author…)
        ("Revision info", {"fields": ("hash", "branch", "date")}),
        # Fieldset 3 : The file
        ("File", {"fields": ("package",)}),
    )


admin.site.register(RevisionItemEntry, RevisionItemEntryAdmin)


class BranchEntryAdmin(admin.ModelAdmin):
    """
    Admin model for Branch entry.
    """

    list_display = ("name", "date", "visible", "stable")
    list_filter = ("date", "visible", "stable")
    ordering = ("-date",)
    # Configuration of edit page
    fieldsets = (
        # Fieldset 1 : name & date
        (
            "Name & date",
            {
                "fields": ("name", "date"),
            },
        ),
        # Fieldset 2 : attributes
        ("Branch info", {"fields": ("visible", "stable")}),
    )


admin.site.register(BranchEntry, BranchEntryAdmin)


# --------------------- The pages -------------------------------------
# Fallback editors only: the pages are edited in the Pages tab of the site admin.


class SiteSettingsAdmin(MarkdownxModelAdmin):
    list_display = ("site_name", "tagline", "content_version")

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class PageSectionAdmin(MarkdownxModelAdmin):
    list_display = ("page", "key", "title", "enabled", "order")
    list_filter = ("page", "enabled")


class ShowcaseImageAdmin(admin.ModelAdmin):
    list_display = ("key", "caption", "style_tag", "in_gallery", "source", "published", "order")
    list_filter = ("source", "published", "in_gallery")


class FeatureCardAdmin(MarkdownxModelAdmin):
    list_display = ("title", "icon", "published", "order")


class SampleGameAdmin(MarkdownxModelAdmin):
    list_display = ("title", "status", "target_version", "published", "order")
    prepopulated_fields = {"slug": ("title",)}


class RoadmapMilestoneAdmin(MarkdownxModelAdmin):
    list_display = ("version", "status", "expected_date", "is_target", "published")


class ReleaseNoteAdmin(MarkdownxModelAdmin):
    list_display = ("branch", "title", "release_date", "published")


class SiteLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "kind", "placement", "published", "order")
    list_filter = ("placement", "kind")


admin.site.register(SiteSettings, SiteSettingsAdmin)
admin.site.register(PageSection, PageSectionAdmin)
admin.site.register(ShowcaseImage, ShowcaseImageAdmin)
admin.site.register(FeatureCard, FeatureCardAdmin)
admin.site.register(SampleGame, SampleGameAdmin)
admin.site.register(RoadmapMilestone, RoadmapMilestoneAdmin)
admin.site.register(ReleaseNote, ReleaseNoteAdmin)
admin.site.register(SiteLink, SiteLinkAdmin)
