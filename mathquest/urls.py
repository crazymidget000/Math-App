from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.accounts import views as account_views

urlpatterns = [
    path("", account_views.home, name="home"),
    path("accounts/signup/", account_views.signup, name="signup"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("apps.game.urls")),
    path("admin/", admin.site.urls),
]
