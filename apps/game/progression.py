"""Pure progression states for stages and monsters in their display order."""

LOCKED = "locked"
UNLOCKED = "unlocked"
DEFEATED = "defeated"


def eligible_monsters(stages, defeated):
    """Return battle-eligible IDs, including eligible replays.

    Only the immediately previous monster and the previous stage's boss gate
    access. Do not require a complete history of earlier wins: demo accounts
    can legitimately have only boss wins recorded.
    """
    eligible = set()
    stage_open = True
    for monsters in stages:
        previous = None
        for monster_id, _is_boss in monsters:
            if stage_open and (previous is None or previous in defeated):
                eligible.add(monster_id)
            previous = monster_id
        bosses = [monster_id for monster_id, is_boss in monsters if is_boss]
        stage_open = bool(bosses) and all(boss_id in defeated for boss_id in bosses)
    return eligible


def monster_states(stages, defeated):
    """Map IDs to display states; each stage contains ordered (ID, is_boss) pairs."""
    eligible = eligible_monsters(stages, defeated)
    return {
        monster_id: DEFEATED
        if monster_id in defeated
        else UNLOCKED
        if monster_id in eligible
        else LOCKED
        for monsters in stages
        for monster_id, _is_boss in monsters
    }
