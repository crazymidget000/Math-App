from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import SignupForm


def home(request):
    return render(request, "home.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("play")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("play")
    return render(request, "accounts/signup.html", {"form": form})
