"""
Forms for user.
"""

from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.forms import EmailInput, TextInput

INPUT_CSS = {"class": "form-group__input"}


class CustomUserCreationForm(UserCreationForm):
    """
    Form for user creation.
    """

    class Meta(UserCreationForm.Meta):
        """
        Meta information.
        """

        fields = UserCreationForm.Meta.fields + ("first_name", "last_name", "email")
        widgets = {
            "username": TextInput(attrs=INPUT_CSS),
            "first_name": TextInput(attrs=INPUT_CSS),
            "last_name": TextInput(attrs=INPUT_CSS),
            "email": EmailInput(attrs=INPUT_CSS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("password1", "password2"):
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update(INPUT_CSS)

    def save(self, commit=True):
        """
        Save function.
        """
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Form for user modification.
    """

    class Meta(UserChangeForm.Meta):
        """
        Meta information.
        """

        fields = ("email", "first_name", "last_name", "password")
        widgets = {
            "email": EmailInput(attrs=INPUT_CSS),
            "first_name": TextInput(attrs=INPUT_CSS),
            "last_name": TextInput(attrs=INPUT_CSS),
        }
