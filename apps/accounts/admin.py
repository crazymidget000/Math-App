from django.contrib import admin

from .models import Player


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("user", "hero", "hero_name", "level", "xp", "coins", "created_at")
    list_filter = ("hero",)
    search_fields = ("user__username", "hero_name")
