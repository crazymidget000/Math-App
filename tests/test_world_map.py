import pytest
from django.contrib.auth.models import User

from apps.accounts.models import Player
from apps.game import services
from apps.game.models import Battle, Monster, Stage
from apps.game.progression import DEFEATED, LOCKED, UNLOCKED, monster_states

# Two stages of three monsters each; the last one in each stage is the boss.
STAGES = [[(1, False), (2, False), (3, True)], [(4, False), (5, False), (6, True)]]


class TestMonsterStates:
    def test_fresh_player_can_only_fight_the_first_monster(self):
        assert monster_states(STAGES, set()) == {
            1: UNLOCKED,
            2: LOCKED,
            3: LOCKED,
            4: LOCKED,
            5: LOCKED,
            6: LOCKED,
        }

    def test_defeating_a_monster_unlocks_the_next_one(self):
        states = monster_states(STAGES, {1})
        assert (states[1], states[2], states[3]) == (DEFEATED, UNLOCKED, LOCKED)

    def test_beating_the_boss_opens_the_next_stage(self):
        states = monster_states(STAGES, {1, 2, 3})
        assert (states[3], states[4], states[5]) == (DEFEATED, UNLOCKED, LOCKED)

    def test_next_stage_stays_locked_until_the_boss_falls(self):
        states = monster_states(STAGES, {1, 2})
        assert (states[3], states[4]) == (UNLOCKED, LOCKED)

    def test_stage_without_a_boss_is_cleared_by_its_last_monster(self):
        stages = [[(1, False), (2, False)], [(3, False)]]
        assert monster_states(stages, {1})[3] == LOCKED
        assert monster_states(stages, {1, 2})[3] == UNLOCKED

    def test_handles_no_stages_and_empty_stages(self):
        assert monster_states([], set()) == {}
        assert monster_states([[], [(1, True)]], set()) == {1: LOCKED}


@pytest.fixture
def hero(client):
    user = User.objects.create_user(username="map-hero", password="dragon-castle-42")
    player = Player.objects.create(user=user, hero="prince")
    client.force_login(user)
    return player


def stage_one():
    return list(Monster.objects.filter(stage__order=1).order_by("order"))


def win(player, monster):
    Battle.objects.create(
        player=player,
        monster=monster,
        player_hp=100,
        player_max_hp=100,
        monster_hp=0,
        monster_max_hp=monster.max_hp,
        status=Battle.Status.WON,
    )


def add_stage(order):
    stage = Stage.objects.create(order=order, slug=f"stage-{order}", name=f"Stage {order} Land")
    return [
        Monster.objects.create(
            stage=stage,
            order=n,
            name=f"S{order} Monster {n}",
            max_hp=60,
            is_boss=n == 2,
            xp_reward=10,
            coin_reward=5,
            question_params={"op": "add", "max_sum": 10},
        )
        for n in (1, 2)
    ]


def states_by_name(player):
    monsters, _ = services.progress_for(player)
    return {m.name: m.state for m in monsters}


@pytest.mark.django_db
class TestWorldMapPage:
    def test_fresh_player_sees_first_monster_ready_and_rest_locked(self, client, hero):
        response = client.get("/play/")
        assert response.status_code == 200
        html = response.content.decode()
        slime, goblin = stage_one()[:2]
        assert f"Battle {slime.name}" in html
        assert f"Battle {goblin.name}" not in html
        assert "🔒 Locked" in html

    def test_defeated_monster_can_be_replayed(self, client, hero):
        slime, goblin = stage_one()[:2]
        win(hero, slime)
        html = client.get("/play/").content.decode()
        assert "✓ Defeated" in html and "Play again" in html
        assert f"Battle {goblin.name}" in html
        response = client.post(f"/play/monsters/{slime.pk}/battle/")
        assert response.status_code == 302
        assert Battle.objects.filter(player=hero, monster=slime, status="active").exists()

    def test_locked_monster_cannot_be_started(self, client, hero):
        goblin = stage_one()[1]
        assert client.post(f"/play/monsters/{goblin.pk}/battle/").status_code == 404

    def test_next_stage_opens_after_boss(self, hero):
        stage_two = add_stage(2)
        assert states_by_name(hero)[stage_two[0].name] == LOCKED
        for monster in stage_one():
            win(hero, monster)
        states = states_by_name(hero)
        assert states[stage_two[0].name] == UNLOCKED
        assert states[stage_two[1].name] == LOCKED

    def test_stages_beyond_playable_limit_stay_locked(self, hero):
        add_stage(2)
        stage_three = add_stage(services.PLAYABLE_STAGE_LIMIT + 1)
        for monster in Monster.objects.filter(stage__order__lte=2):
            win(hero, monster)
        assert states_by_name(hero)[stage_three[0].name] == LOCKED

    def test_page_works_for_users_without_a_player(self, client):
        admin = User.objects.create_superuser(username="map-admin", password="x-long-pass-99")
        client.force_login(admin)
        assert client.get("/play/").status_code == 200

    def test_progress_uses_two_queries(self, hero, django_assert_num_queries):
        add_stage(2)
        with django_assert_num_queries(2):
            services.progress_for(hero)
