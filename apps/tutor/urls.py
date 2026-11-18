from django.urls import path

from . import views

urlpatterns = [path("battle/<int:battle_id>/hint/", views.hint, name="battle_hint")]
