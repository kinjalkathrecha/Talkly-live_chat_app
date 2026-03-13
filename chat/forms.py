from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class UserSignUpForm(UserCreationForm):
    phone_number = forms.CharField(max_length=15, required=True, help_text="Required for others to find you.")

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('phone_number',)

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone_number = self.cleaned_data.get('phone_number')
            profile.save()
        return user

class AddContactForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100, required=False)
    phone_number = forms.CharField(max_length=15)
