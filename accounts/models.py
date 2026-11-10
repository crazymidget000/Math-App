from django.conf import settings
from django.db import models


class Player(models.Model):
    class Hero(models.TextChoices):
        PRINCE = "prince", "Prince"
        PRINCESS = "princess", "Princess"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="player"
    )
    hero = models.CharField(max_length=10, choices=Hero.choices)
    hero_name = models.CharField(max_length=20, default="Hero")
    level = models.PositiveIntegerField(default=1)
    xp = models.PositiveIntegerField(default=0)
    coins = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_hero_display()})"
