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
