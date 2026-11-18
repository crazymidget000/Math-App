"""Map navigation and access regressions for the missing progression module."""

import pytest
from django.contrib.auth.models import User

from apps.accounts.models import Player
from apps.game import progression, services
from apps.game.models import Battle, Monster, Stage


def test_initial_states_and_sequential_monster_unlocks():
    stages = [[(1, False), (2, True)], [(3, False), (4, True)]]
    assert progression.monster_states(stages, set()) == {
        1: "unlocked",
        2: "locked",
        3: "locked",
        4: "locked",
    }
    assert progression.monster_states(stages, {1}) == {
        1: "defeated",
        2: "unlocked",
        3: "locked",
        4: "locked",
    }
    assert progression.monster_states(stages, {1, 2}) == {
        1: "defeated",
        2: "defeated",
        3: "unlocked",
        4: "locked",
    }
    assert progression.monster_states(stages, {1, 2, 3, 4}) == dict.fromkeys(
        [1, 2, 3, 4], "defeated"
    )


def test_boss_only_history_unlocks_next_stage_without_requiring_all_prior_wins():
    stages = [[(1, False), (2, True)], [(3, False), (4, True)]]
    assert progression.monster_states(stages, {2}) == {
        1: "unlocked",
        2: "defeated",
        3: "unlocked",
        4: "locked",
    }
    assert progression.eligible_monsters(stages, {2}) == {1, 3}


def test_only_immediate_predecessor_is_required_and_defeated_state_is_separate():
    stages = [[(1, False), (2, False), (3, True)]]
    assert progression.monster_states(stages, {2}) == {1: "unlocked", 2: "defeated", 3: "unlocked"}
    assert progression.eligible_monsters(stages, {2}) == {1, 3}


@pytest.mark.parametrize("first_stage", [[], [(1, False)]])
def test_missing_boss_keeps_following_stage_locked(first_stage):
    states = progression.monster_states([first_stage, [(2, True)]], {1})
    assert states[2] == "locked"
    assert progression.monster_states([], set()) == {}


@pytest.fixture
def map_player(client, db):
    user = User.objects.create_user(username="map-player")
    player = Player.objects.create(user=user, hero="princess")
    client.force_login(user)
    return player


def record_win(player, monster):
    return Battle.objects.create(
        player=player,
        monster=monster,
        player_hp=100,
        player_max_hp=100,
        monster_hp=0,
        monster_max_hp=monster.max_hp,
        status=Battle.Status.WON,
    )


def add_stage(order):
    stage = Stage.objects.create(
        order=order, slug=f"stage-{order}", name=f"Stage {order}", operation="sub"
    )
    return Monster.objects.create(
        stage=stage,
        order=1,
        name=f"Boss {order}",
        max_hp=60,
        attack=15,
        is_boss=True,
        xp_reward=40,
        coin_reward=10,
        question_params={"op": "sub", "max_a": 10},
    )


def test_authenticated_map_renders_and_locked_direct_post_is_rejected(client, map_player):
    monsters = list(Monster.objects.order_by("order"))
    response = client.get("/play/")
    assert response.status_code == 200
    assert [m.state for m in response.context["monsters"]] == [
        "unlocked",
        "locked",
        "locked",
        "locked",
    ]
    assert b"Battle Slime" in response.content
    assert b"Battle Goblin" not in response.content
    assert client.post(f"/play/monsters/{monsters[1].pk}/battle/").status_code == 404
    assert not Battle.objects.exists()


def test_winning_updates_map_and_preserves_replay(client, map_player):
    slime = Monster.objects.get(order=1)
    battle = services.start_battle(map_player.user, slime.pk)
    while battle.status == Battle.Status.ACTIVE:
        question = battle.questions.get(answered_at=None)
        battle = services.answer_question(
            map_player.user, battle.pk, question.pk, question.correct_answer
        )
    response = client.get("/play/")
    assert [m.state for m in response.context["monsters"]][:2] == ["defeated", "unlocked"]
    assert b"Play Slime again" in response.content
    assert b"Battle Goblin" in response.content
    replay = client.post(f"/play/monsters/{slime.pk}/battle/")
    assert replay.status_code == 302
    assert Battle.objects.filter(player=map_player, monster=slime).count() == 2


def test_previous_stage_boss_gates_next_stage_and_later_content_stays_locked(client, map_player):
    second_boss = add_stage(2)
    third_boss = add_stage(3)
    for monster in Monster.objects.filter(stage__order=1, is_boss=False):
        record_win(map_player, monster)
    monsters, _ = services.progress_for(map_player)
    assert next(m for m in monsters if m.pk == second_boss.pk).state == "locked"
    record_win(map_player, Monster.objects.get(stage__order=1, is_boss=True))
    response = client.get("/play/")
    assert response.status_code == 200
    assert response.context["stages"][1]["open"]
    assert not response.context["stages"][2]["open"]
    assert client.post(f"/play/monsters/{second_boss.pk}/battle/").status_code == 302
    active = Battle.objects.get(player=map_player, status="active")
    services.flee_battle(map_player.user, active.pk)
    record_win(map_player, second_boss)
    # Even historical data must not open operations that the app cannot play yet.
    record_win(map_player, third_boss)
    monsters, _ = services.progress_for(map_player)
    third = next(m for m in monsters if m.pk == third_boss.pk)
    assert (third.state, third.unlocked) == ("locked", False)
    assert client.post(f"/play/monsters/{third.pk}/battle/").status_code == 404


def test_other_players_wins_and_lost_battles_do_not_unlock(client, map_player):
    other = Player.objects.create(
        user=User.objects.create_user(username="other-map"), hero="prince"
    )
    slime = Monster.objects.get(order=1)
    record_win(other, slime)
    loss = record_win(map_player, slime)
    loss.status = Battle.Status.LOST
    loss.save()
    response = client.get("/play/")
    assert [m.state for m in response.context["monsters"]][:2] == ["unlocked", "locked"]


def test_boss_only_demo_progress_opens_next_stage_in_map_and_direct_post(client, map_player):
    second_boss = add_stage(2)
    first_boss = Monster.objects.get(stage__order=1, is_boss=True)
    record_win(map_player, first_boss)
    response = client.get("/play/")
    boss_state = next(m for m in response.context["monsters"] if m.pk == first_boss.pk)
    assert boss_state.state == "defeated"
    assert not boss_state.unlocked
    assert b"Play Meadow Dragon again" not in response.content
    assert response.context["stages"][1]["open"]
    assert client.post(f"/play/monsters/{second_boss.pk}/battle/").status_code == 302


def test_historical_win_in_locked_stage_does_not_open_header_or_replay(client, map_player):
    second_boss = add_stage(2)
    record_win(map_player, second_boss)
    response = client.get("/play/")
    second = response.context["stages"][1]
    assert second["monsters"][0].state == "defeated"
    assert not second["open"]
    assert not second["monsters"][0].unlocked
    assert b"Play Boss 2 again" not in response.content
    assert client.post(f"/play/monsters/{second_boss.pk}/battle/").status_code == 404


def test_map_uses_two_progress_queries(map_player, django_assert_num_queries):
    with django_assert_num_queries(2):
        monsters, stages = services.progress_for(map_player)
    assert len(monsters) == 4 and len(stages) == 1


@pytest.mark.django_db
def test_missing_profile_and_empty_map_do_not_raise(client):
    user = User.objects.create_user(username="missing-profile")
    client.force_login(user)
    response = client.get("/play/")
    assert response.status_code == 200
    assert b'button type="submit">Battle' not in response.content
    Monster.objects.all().delete()
    response = client.get("/play/")
    assert response.status_code == 200
    assert b"The world is being prepared" in response.content


def test_anonymous_map_requires_login(client):
    response = client.get("/play/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.url
