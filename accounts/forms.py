from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import Player


class SignupForm(UserCreationForm):
    hero = forms.ChoiceField(
        choices=Player.Hero.choices,
        widget=forms.RadioSelect,
        label="Pick your hero",
    )

    class Meta(UserCreationForm.Meta):
        fields = ("username",)

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Player.objects.create(user=user, hero=self.cleaned_data["hero"])
        return user
