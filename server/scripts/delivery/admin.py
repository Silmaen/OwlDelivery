"""
Administration page
"""

from django.contrib import admin
from markdownx.admin import MarkdownxModelAdmin

from .models import *


# --------------------- The news -------------------------------------


class NewsEntryAdmin(MarkdownxModelAdmin):
    """
    Admin page for news
    """

    list_display = ("title", "author", "date", "content_overview")
    list_filter = (
        "author",
        "date",
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
                "fields": ("title", "slug", "author", "date"),
            },
        ),
        # Fieldset 2 : article content
        ("Content of the article", {"fields": ("content",)}),
    )

    def save_model(self, request, obj, form, change):
        obj.author = request.user
        super(NewsEntryAdmin, self).save_model(request, obj, form, change)

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
        super(NewsCommentAdmin, self).save_model(request, obj, form, change)


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
