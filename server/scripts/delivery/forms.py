"""
forms for delivery
"""

from markdownx.forms import forms
from markdownx.widgets import MarkdownxWidget

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

INPUT_CSS = {"class": "form-group__input"}


class NewsEntryForm(forms.ModelForm):
    """
    Form for news creation.
    """

    class Meta:
        """
        Meta information
        """

        model = NewsEntry
        fields = (
            "title",
            "content",
            "published",
        )
        widgets = {
            "title": forms.TextInput(attrs=INPUT_CSS),
            "published": forms.CheckboxInput(attrs=INPUT_CSS),
        }


class NewsCommentForm(forms.ModelForm):
    """
    Form for news commentcreation.
    """

    class Meta:
        """
        Meta information
        """

        model = NewsComment
        fields = ("content",)


class RevisionItemEntryForm(forms.ModelForm):
    """
    Form for Revision entry.
    """

    class Meta:
        """
        Meta information
        """

        model = RevisionItemEntry
        fields = ("hash", "branch", "name", "flavor_name", "date", "rev_type")
        widgets = {
            "hash": forms.TextInput(attrs=INPUT_CSS),
            "branch": forms.TextInput(attrs=INPUT_CSS),
            "name": forms.TextInput(attrs=INPUT_CSS),
            "flavor_name": forms.TextInput(attrs=INPUT_CSS),
            "date": forms.DateTimeInput(attrs=INPUT_CSS),
            "rev_type": forms.Select(attrs=INPUT_CSS),
        }


class RevisionItemEntryFullForm(forms.ModelForm):
    """
    Form for Revision entry.
    """

    class Meta:
        """
        Meta information
        """

        model = RevisionItemEntry
        fields = (
            "hash",
            "branch",
            "name",
            "flavor_name",
            "date",
            "rev_type",
            "package",
        )
        widgets = {
            "hash": forms.TextInput(attrs=INPUT_CSS),
            "branch": forms.TextInput(attrs=INPUT_CSS),
            "name": forms.TextInput(attrs=INPUT_CSS),
            "flavor_name": forms.TextInput(attrs=INPUT_CSS),
            "date": forms.DateTimeInput(attrs=INPUT_CSS),
            "rev_type": forms.Select(attrs=INPUT_CSS),
            "package": forms.ClearableFileInput(attrs=INPUT_CSS),
        }


class BranchEntryForm(forms.ModelForm):
    """
    Form for Revision entry.
    """

    class Meta:
        """
        Meta information
        """

        model = BranchEntry
        fields = (
            "name",
            "date",
            "visible",
            "stable",
        )
        widgets = {
            "name": forms.TextInput(attrs=INPUT_CSS),
            "date": forms.DateTimeInput(attrs=INPUT_CSS),
            "visible": forms.CheckboxInput(attrs={"class": "form-group__input"}),
            "stable": forms.CheckboxInput(attrs={"class": "form-group__input"}),
        }


# --------------------- The pages -------------------------------------


class PageContentForm(forms.ModelForm):
    """
    Form of a page content row: `INPUT_CSS` on every widget but the markdown editor.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, MarkdownxWidget):
                field.widget.attrs.update(INPUT_CSS)


DATE_INPUT = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class SiteSettingsForm(PageContentForm):
    class Meta:
        model = SiteSettings
        fields = (
            "site_name",
            "tagline",
            "pitch",
            "meta_description",
            "hero_image",
            "social_image",
            "cta_discover_label",
            "cta_download_label",
            "cta_docs_label",
            "cta_github_label",
            "news_count",
            "roadmap_teaser_count",
            "show_dev_build",
            "footer_text",
        )


class PageSectionForm(PageContentForm):
    class Meta:
        model = PageSection
        fields = ("title", "intro", "enabled", "order")


class ShowcaseImageForm(PageContentForm):
    class Meta:
        model = ShowcaseImage
        fields = ("key", "image", "caption", "alt_text", "style_tag", "in_gallery", "published", "order")


class FeatureCardForm(PageContentForm):
    class Meta:
        model = FeatureCard
        fields = ("title", "icon", "body", "image", "link_label", "link_url", "published", "order")


class SampleGameForm(PageContentForm):
    class Meta:
        model = SampleGame
        fields = (
            "title",
            "slug",
            "inspired_by",
            "summary",
            "exercises",
            "image",
            "link_url",
            "status",
            "target_version",
            "published",
            "order",
        )


class RoadmapMilestoneForm(PageContentForm):
    class Meta:
        model = RoadmapMilestone
        fields = ("version", "goal", "highlights", "expected_date", "status", "is_target", "link_url", "published")
        widgets = {"expected_date": DATE_INPUT}


class ReleaseNoteForm(PageContentForm):
    class Meta:
        model = ReleaseNote
        fields = ("branch", "title", "release_date", "highlights", "changelog_url", "news", "published")
        widgets = {"release_date": DATE_INPUT}


class SiteLinkForm(PageContentForm):
    class Meta:
        model = SiteLink
        fields = ("label", "kind", "url", "icon", "placement", "published", "order")
