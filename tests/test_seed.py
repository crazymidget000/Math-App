from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command

from apps.accounts.models import Player


@pytest.fixture
def seed_env(monkeypatch):
    monkeypatch.setenv("SEED_GRADER_PASSWORD", "grader-pass-1")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin-pass-1")
    return monkeypatch


def seed():
    call_command("seed", stdout=StringIO())


@pytest.mark.django_db
class TestSeed:
    @pytest.mark.parametrize("missing", ["SEED_GRADER_PASSWORD", "SEED_ADMIN_PASSWORD"])
    def test_refuses_to_run_without_passwords(self, seed_env, missing):
        seed_env.delenv(missing)
        with pytest.raises(CommandError, match=missing):
            seed()
        assert not User.objects.exists()

    def test_creates_grader_as_fresh_player(self, seed_env):
        seed()
        grader = User.objects.get(username="grader")
        assert grader.check_password("grader-pass-1")
        assert not grader.is_staff and not grader.is_superuser
        assert grader.email == ""
        assert (grader.player.level, grader.player.xp, grader.player.coins) == (1, 0, 0)

    def test_creates_admin_with_admin_rights(self, seed_env):
        seed()
        admin = User.objects.get(username="admin")
        assert admin.check_password("admin-pass-1")
        assert admin.is_staff and admin.is_superuser
        assert admin.email == ""

    def test_running_twice_creates_no_duplicates(self, seed_env):
        seed()
        seed()
        assert User.objects.count() == 2
        assert Player.objects.count() == 1

    def test_rerun_applies_changed_passwords(self, seed_env):
        seed()
        seed_env.setenv("SEED_GRADER_PASSWORD", "grader-pass-2")
        seed_env.setenv("SEED_ADMIN_PASSWORD", "admin-pass-2")
        seed()
        assert User.objects.get(username="grader").check_password("grader-pass-2")
        assert User.objects.get(username="admin").check_password("admin-pass-2")

    def test_rerun_keeps_password_hash_when_unchanged(self, seed_env):
        seed()
        before = User.objects.get(username="grader").password
        seed()
        assert User.objects.get(username="grader").password == before

    def test_rerun_restores_admin_rights(self, seed_env):
        seed()
        User.objects.filter(username="admin").update(is_staff=False, is_superuser=False)
        seed()
        admin = User.objects.get(username="admin")
        assert admin.is_staff and admin.is_superuser

    def test_rerun_keeps_grader_progress(self, seed_env):
        seed()
        Player.objects.filter(user__username="grader").update(level=3, xp=50, coins=40)
        seed()
        player = Player.objects.get(user__username="grader")
        assert (player.level, player.xp, player.coins) == (3, 50, 40)

    def test_grader_can_log_in_and_play(self, seed_env, client):
        seed()
        response = client.post(
            "/accounts/login/", {"username": "grader", "password": "grader-pass-1"}
        )
        assert response.url == "/play/"
        assert client.get("/play/").status_code == 200
