from uuid import uuid4

from django.db import models
from django.utils import timezone


class ABVisitor(models.Model):
    class Variant(models.TextChoices):
        KUDOS = "kudos"
        THANKS = "thanks"

    visitor_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    variant = models.CharField(max_length=6, choices=Variant.choices)
    impression_at = models.DateTimeField(default=timezone.now)
    clicked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.variant} visitor {self.visitor_id}"
