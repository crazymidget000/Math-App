import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Player

PASSWORD_VARS = ("SEED_GRADER_PASSWORD", "SEED_ADMIN_PASSWORD")


class Command(BaseCommand):
    help = "Create or update the grader accounts. Safe to run any number of times."

    @transaction.atomic
    def handle(self, *args, **options):
        missing = [name for name in PASSWORD_VARS if not os.environ.get(name)]
        if missing:
            raise CommandError(f"Set {' and '.join(missing)} first.")

        grader = self.upsert_user("grader", os.environ["SEED_GRADER_PASSWORD"], is_admin=False)
        Player.objects.get_or_create(user=grader, defaults={"hero": Player.Hero.PRINCESS})

        self.upsert_user("admin", os.environ["SEED_ADMIN_PASSWORD"], is_admin=True)

        self.stdout.write(self.style.SUCCESS("Seed complete."))

    def upsert_user(self, username, password, is_admin):
        user, created = get_user_model().objects.update_or_create(
            username=username,
            defaults={"is_staff": is_admin, "is_superuser": is_admin, "is_active": True},
        )
        # Re-hashing an unchanged password would log out everyone using this account.
        if created or not user.check_password(password):
            user.set_password(password)
            user.save(update_fields=["password"])
        self.stdout.write(f"{'Created' if created else 'Updated'}: {username}")
        return user
