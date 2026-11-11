
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Player


class Command(BaseCommand):
    help = "Create grader accounts and demo player data"

    @transaction.atomic
    def handle(self, *args, **options):
        admin_password = os.environ.get("SEED_ADMIN_PASSWORD")
        player_password = os.environ.get("SEED_PLAYER_PASSWORD")

        if not admin_password or not player_password:
            raise CommandError(
                "Set SEED_ADMIN_PASSWORD and SEED_PLAYER_PASSWORD first."
            )

        User = get_user_model()

        accounts = [
            ("admin@example.com", admin_password, True),
            ("player@example.com", player_password, False),
        ]

        for email, password, is_admin in accounts:
            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    "email": email,
                    "is_staff": is_admin,
                    "is_superuser": is_admin,
                },
            )

            if created:
                user.set_password(password)
                user.save(update_fields=["password"])

            if not is_admin:
                Player.objects.get_or_create(
                    user=user,
                    defaults={
                        "hero": Player.Hero.PRINCE,
                        "hero_name": "Demo Hero",
                        "level": 1,
                        "xp": 0,
                        "coins": 100,
                    },
                )

            status = "Created" if created else "Already exists"
            self.stdout.write(f"{status}: {email}")

        self.stdout.write(
            self.style.SUCCESS("Seed completed successfully!")
        )
