"""
Forms for user.
"""

from django.contrib.auth.forms import UserCreationForm, UserChangeForm


class CustomUserCreationForm(UserCreationForm):
    """
    Form for user creation.
    """

    class Meta(UserCreationForm.Meta):
        """
        Meta information.
        """

        fields = UserCreationForm.Meta.fields + ("first_name", "last_name", "email")

    def save(self, commit=True):
        """
        Save function.
        """
        user = super(CustomUserCreationForm, self).save(commit=False)
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
