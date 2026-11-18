"""PostgreSQL verifies duplicate hints do not duplicate external calls or block play."""

from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from threading import Event
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.contrib.auth.models import User
from django.db import close_old_connections, connection, connections

from apps.accounts.models import Player
from apps.game import services as game_services
from apps.game.models import Monster, Question
from apps.tutor import services
from apps.tutor.client import fallback_hint
from apps.tutor.models import HintRequest


@pytest.mark.django_db(transaction=True)
def test_simultaneous_hints_share_result_while_next_answer_still_works(monkeypatch):
    if connection.vendor != "postgresql":
        pytest.skip("requires PostgreSQL row locks")
    import_module("apps.game.migrations.0002_stage_one_content").seed_stage_one(
        apps, SimpleNamespace(connection=connection)
    )
    user = User.objects.create_user(username="concurrent-wizard")
    Player.objects.create(user=user, hero="prince")
    battle = game_services.start_battle(user, Monster.objects.get(order=1).pk)
    wrong = battle.questions.get()
    game_services.answer_question(user, battle.pk, wrong.pk, wrong.correct_answer + 1)
    next_question = battle.questions.get(answered_at=None)
    entered, release, second_started = Event(), Event(), Event()
    calls = []

    def provider(question):
        calls.append(question.pk)
        entered.set()
        assert release.wait(timeout=10)
        return fallback_hint(question.operation), "ok"

    monkeypatch.setattr("apps.tutor.client.request_hint", provider)

    def request_hint(second=False):
        close_old_connections()
        try:
            if second:
                second_started.set()
            return services.hint_for_question(Question.objects.get(pk=wrong.pk)).pk
        finally:
            connections.close_all()

    def answer_next():
        close_old_connections()
        try:
            return game_services.answer_question(
                user, battle.pk, next_question.pk, next_question.correct_answer
            ).monster_hp
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(request_hint)
        try:
            assert entered.wait(timeout=5)
            duplicate = pool.submit(request_hint, True)
            assert second_started.wait(timeout=5)
            assert pool.submit(answer_next).result(timeout=5) < battle.monster_hp
        finally:
            release.set()
        assert first.result(timeout=5) == duplicate.result(timeout=5)
    assert calls == [wrong.pk]
    assert HintRequest.objects.filter(question=wrong).count() == 1
