from django.urls import path

from . import views

app_name = "abtest"

# First seven hexadecimal digits of SHA-1("inner-wrath").
urlpatterns = [
    path("f48c8ec", views.page, name="page"),
    path("f48c8ec/click", views.click, name="click"),
    path("f48c8ec/stats", views.stats, name="stats"),
]
