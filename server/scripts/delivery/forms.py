"""
forms for delivery
"""

from markdownx.forms import forms

from .models import BranchEntry, NewsComment, NewsEntry, RevisionItemEntry

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
        )
        widgets = {
            "title": forms.TextInput(attrs=INPUT_CSS),
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
