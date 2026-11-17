import pytest

from apps.game import rules


@pytest.mark.parametrize("level,hp", [(1, 100), (2, 110), (10, 190)])
def test_max_hp(level, hp):
    assert rules.hero_max_hp(level) == hp


@pytest.mark.parametrize(
    "correct,ms,attack,dealt,taken",
    [
        (True, 0, 15, 30, 0),
        (True, 6000, 15, 30, 0),
        (True, 6001, 15, 20, 0),
        (False, 1, 15, 0, 15),
        (False, 9000, 20, 0, 20),
    ],
)
def test_damage(correct, ms, attack, dealt, taken):
    turn = rules.resolve_turn(100, 60, correct, ms, attack)
    assert (turn.damage_dealt, turn.damage_taken) == (dealt, taken)
    assert (turn.player_hp, turn.monster_hp) == (100 - taken, 60 - dealt)
    assert turn.status == "active"


def test_win_and_loss_clamp_hp():
    win = rules.resolve_turn(100, 10, True, 8000, 15)
    loss = rules.resolve_turn(10, 60, False, 8000, 15)
    assert (win.monster_hp, win.status) == (0, "won")
    assert (loss.player_hp, loss.status) == (0, "lost")


@pytest.mark.parametrize("xp,reward,level,left", [(0, 40, 1, 40), (90, 10, 2, 0), (90, 250, 3, 40)])
def test_level_progress(xp, reward, level, left):
    assert rules.add_xp(1, xp, reward) == (level, left)


@pytest.mark.parametrize(
    "args", [(0, 60, True, 0, 15), (100, 0, True, 0, 15), (100, 60, True, -1, 15)]
)
def test_invalid_turn(args):
    with pytest.raises(ValueError):
        rules.resolve_turn(*args)
