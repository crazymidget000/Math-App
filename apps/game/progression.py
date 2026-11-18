"""Pure progression rules (no database): which monsters are locked, unlocked or defeated.

Plan §5: stage 1 is always open; stage n opens when stage n-1's boss is defeated. Inside an
open stage, the first monster is unlocked and each later one unlocks when the one before it
is defeated.
"""

LOCKED = "locked"
UNLOCKED = "unlocked"
DEFEATED = "defeated"


def monster_states(stages, defeated):
    """Map each monster id to LOCKED, UNLOCKED or DEFEATED.

    stages: stages in play order, each a list of (monster_id, is_boss) in monster order.
    defeated: ids of monsters the player has won a battle against.
    """
    states = {}
    stage_open = True
    for monsters in stages:
        previous_defeated = True
        for monster_id, _ in monsters:
            if not stage_open:
                states[monster_id] = LOCKED
            elif monster_id in defeated:
                states[monster_id] = DEFEATED
            elif previous_defeated:
                states[monster_id] = UNLOCKED
            else:
                states[monster_id] = LOCKED
            previous_defeated = monster_id in defeated
        stage_open = stage_open and _stage_cleared(monsters, defeated)
    return states


def _stage_cleared(monsters, defeated):
    if not monsters:
        return False
    bosses = [monster_id for monster_id, is_boss in monsters if is_boss]
    # A stage without a boss is cleared by its last monster.
    gate = bosses or [monsters[-1][0]]
    return all(monster_id in defeated for monster_id in gate)
