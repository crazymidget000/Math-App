from django.urls import path

from . import views

urlpatterns = [
    path("play/", views.play, name="play"),
    path("play/monsters/<int:monster_id>/battle/", views.start, name="start_battle"),
    path("battle/<int:battle_id>/", views.battle_detail, name="battle"),
    path("battle/<int:battle_id>/answer/", views.answer, name="answer"),
    path("battle/<int:battle_id>/flee/", views.flee, name="flee"),
]
