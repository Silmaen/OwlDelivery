"""
forms for delivery
"""

from markdownx.forms import forms

from .models import *


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
