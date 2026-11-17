from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Player
from apps.game import services
from apps.game.models import Battle, Monster, Question, Stage

pytestmark = pytest.mark.django_db


@pytest.fixture
def hero(client):
    user = User.objects.create_user(username="battle-hero", password="dragon-castle-42")
    player = Player.objects.create(user=user, hero="princess")
    client.force_login(user)
    return player


@pytest.fixture
def slime():
    return Monster.objects.get(stage__order=1, order=1)


def start(client, monster):
    response = client.post(f"/play/monsters/{monster.pk}/battle/")
    assert response.status_code == 302
    return Battle.objects.get(pk=response.url.split("/")[2])


def submit(client, battle, correct=True, **headers):
    q = battle.questions.get(answered_at=None)
    response = client.post(
        f"/battle/{battle.pk}/answer/",
        {
            "question_id": q.pk,
            "answer": q.correct_answer if correct else q.correct_answer + 1,
        },
        **headers,
    )
    battle.refresh_from_db()
    q.refresh_from_db()
    return response, q


def test_migration_seeds_all_monsters_idempotently():
    seed = import_module("apps.game.migrations.0002_stage_one_content").seed_stage_one
    seed(apps, SimpleNamespace(connection=connection))
    seed(apps, SimpleNamespace(connection=connection))
    assert Stage.objects.count() == 1
    assert Monster.objects.count() == 4
    assert list(Monster.objects.values_list("max_hp", flat=True)) == [60, 80, 100, 140]
    assert Monster.objects.get(order=4).question_params["max_sum"] == 100


def test_start_resume_and_locked_monsters(client, hero, slime):
    battle = start(client, slime)
    assert (battle.player_hp, battle.monster_hp) == (100, 60)
    assert battle.questions.count() == 1
    assert start(client, slime).pk == battle.pk
    goblin = Monster.objects.get(order=2)
    assert client.post(f"/play/monsters/{goblin.pk}/battle/").status_code == 404
    assert Battle.objects.count() == 1
    content = client.get("/play/").content.decode()
    assert "Resume your battle" in content


def test_answer_hidden_until_wrong_and_htmx_returns_partial(client, hero, slime):
    battle = start(client, slime)
    q = battle.questions.get()
    q.prompt, q.correct_answer = "20 + 23", 43
    q.save()
    html = client.get(f"/battle/{battle.pk}/").content.decode()
    assert "20 + 23" in html
    assert "43" not in html
    response, q = submit(client, battle, correct=False, HTTP_HX_REQUEST="true")
    html = response.content.decode()
    assert response.status_code == 200
    assert "<html" not in html
    assert "<strong>43</strong>" in html
    assert (battle.player_hp, battle.monster_hp) == (85, 60)
    assert q.damage_taken == 15
    assert battle.questions.filter(answered_at=None).count() == 1


def test_server_timing_and_duplicate_submission(client, hero, slime):
    battle = start(client, slime)
    q = battle.questions.get()
    Question.objects.filter(pk=q.pk).update(created_at=timezone.now() - timedelta(seconds=7))
    response, q = submit(client, battle)
    assert response.status_code == 302
    assert q.response_ms >= 7000
    assert battle.monster_hp == 40
    client.post(
        f"/battle/{battle.pk}/answer/",
        {
            "question_id": q.pk,
            "answer": q.correct_answer,
            "response_ms": 0,
        },
    )
    battle.refresh_from_db()
    assert battle.monster_hp == 40
    assert battle.questions.count() == 2


def test_win_awards_once_levels_up_and_unlocks(client, hero, slime):
    hero.xp = 90
    hero.save()
    battle = start(client, slime)
    while battle.status == "active":
        _, last = submit(client, battle)
    hero.refresh_from_db()
    assert battle.status == "won"
    assert battle.monster_hp == 0
    assert battle.ended_at is not None
    assert (hero.level, hero.xp, hero.coins) == (2, 30, 10)
    assert battle.leveled_up
    assert not battle.questions.filter(answered_at=None).exists()
    client.post(
        f"/battle/{battle.pk}/answer/",
        {
            "question_id": last.pk,
            "answer": last.correct_answer,
        },
    )
    hero.refresh_from_db()
    assert (hero.xp, hero.coins) == (30, 10)
    html = client.get(f"/battle/{battle.pk}/").content.decode()
    assert "Victory!" in html and "Level up!" in html
    goblin_battle = start(client, Monster.objects.get(order=2))
    assert goblin_battle.player_max_hp == 110


def test_loss_retry_and_flee_preserve_rewards(client, hero, slime):
    battle = start(client, slime)
    while battle.status == "active":
        submit(client, battle, correct=False)
    assert battle.status == "lost"
    assert battle.player_hp == 0
    assert "Try again" in client.get(f"/battle/{battle.pk}/").content.decode()
    retry = start(client, slime)
    assert retry.pk != battle.pk and retry.player_hp == 100
    assert client.post(f"/battle/{retry.pk}/flee/").status_code == 302
    client.post(f"/battle/{retry.pk}/flee/")
    retry.refresh_from_db()
    assert retry.status == "fled" and retry.ended_at is not None
    q = retry.questions.get()
    client.post(f"/battle/{retry.pk}/answer/", {"question_id": q.pk, "answer": q.correct_answer})
    q.refresh_from_db()
    assert q.answered_at is None
    hero.refresh_from_db()
    assert (hero.level, hero.xp, hero.coins) == (1, 0, 0)


@pytest.mark.parametrize("value", ["", "nope", "1.5", "-1", "999999999999999999999"])
def test_bad_answers_do_not_change_state(client, hero, slime, value):
    battle = start(client, slime)
    q = battle.questions.get()
    response = client.post(f"/battle/{battle.pk}/answer/", {"question_id": q.pk, "answer": value})
    assert response.status_code == 200
    assert response.context["form"].errors
    battle.refresh_from_db()
    q.refresh_from_db()
    assert (battle.player_hp, battle.monster_hp, q.answered_at) == (100, 60, None)


def test_other_players_cannot_read_answer_or_flee(client, hero, slime):
    battle = start(client, slime)
    q = battle.questions.get()
    other = User.objects.create_user(username="other")
    Player.objects.create(user=other, hero="prince")
    client.force_login(other)
    assert client.get(f"/battle/{battle.pk}/").status_code == 404
    assert (
        client.post(
            f"/battle/{battle.pk}/answer/",
            {
                "question_id": q.pk,
                "answer": q.correct_answer,
            },
        ).status_code
        == 404
    )
    assert client.post(f"/battle/{battle.pk}/flee/").status_code == 404
    client.logout()
    assert client.get(f"/battle/{battle.pk}/").status_code == 302
    assert client.post(f"/play/monsters/{slime.pk}/battle/").status_code == 302


def test_post_only_and_csrf(client, hero, slime):
    battle = start(client, slime)
    paths = [
        f"/play/monsters/{slime.pk}/battle/",
        f"/battle/{battle.pk}/answer/",
        f"/battle/{battle.pk}/flee/",
    ]
    protected = Client(enforce_csrf_checks=True)
    protected.force_login(hero.user)
    for path in paths:
        assert client.get(path).status_code == 405
        assert protected.post(path).status_code == 403


def test_question_must_belong_to_battle(client, hero, slime):
    old = start(client, slime)
    old_question = old.questions.get()
    client.post(f"/battle/{old.pk}/flee/")
    new = start(client, slime)
    assert (
        client.post(
            f"/battle/{new.pk}/answer/",
            {
                "question_id": old_question.pk,
                "answer": old_question.correct_answer,
            },
        ).status_code
        == 404
    )


def test_no_consecutive_repeat(client, hero, slime, monkeypatch):
    battle = start(client, slime)
    previous = battle.questions.get()
    from apps.game.generator import GeneratedQuestion

    sequence = iter(
        [
            GeneratedQuestion(previous.prompt, previous.operand_a, previous.operand_b, "add", 0),
            GeneratedQuestion("4 + 5" if previous.prompt != "4 + 5" else "5 + 4", 4, 5, "add", 9),
        ]
    )
    monkeypatch.setattr(services, "generate_question", lambda *args: next(sequence))
    submit(client, battle, correct=False)
    assert battle.questions.get(answered_at=None).prompt != previous.prompt


def test_entire_stage_is_playable(client, hero):
    for monster in Monster.objects.all():
        battle = start(client, monster)
        while battle.status == "active":
            response, _ = submit(client, battle)
            assert response.status_code == 302
        assert battle.status == "won"
    assert Battle.objects.filter(player=hero, status="won").count() == 4
    assert "Addition Meadow complete" in client.get(f"/battle/{battle.pk}/").content.decode()
