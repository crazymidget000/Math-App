"""Run against PostgreSQL to exercise real row locking, not SQLite's fallback."""

from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from threading import Barrier
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.contrib.auth.models import User
from django.db import close_old_connections, connection

from apps.accounts.models import Player
from apps.game import services
from apps.game.models import Battle, Monster


@pytest.mark.django_db(transaction=True)
def test_concurrent_winning_answers_award_once():
    if connection.vendor != "postgresql":
        pytest.skip("requires PostgreSQL row locks")
    import_module("apps.game.migrations.0002_stage_one_content").seed_stage_one(
        apps, SimpleNamespace(connection=connection)
    )
    user = User.objects.create_user(username="concurrent-player")
    player = Player.objects.create(user=user, hero="prince")
    battle = services.start_battle(user, Monster.objects.get(order=1).pk)
    Battle.objects.filter(pk=battle.pk).update(monster_hp=20)
    question = battle.questions.get()
    barrier = Barrier(2)

    def answer():
        close_old_connections()
        try:
            thread_user = User.objects.get(pk=user.pk)
            barrier.wait(timeout=10)
            return services.answer_question(
                thread_user, battle.pk, question.pk, question.correct_answer
            ).status
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: answer(), range(2)))
    assert results == ["won", "won"]
    player.refresh_from_db()
    assert (player.xp, player.coins) == (40, 10)
    assert battle.questions.count() == 1
