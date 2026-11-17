"""Pure battle calculations; all times are measured server-side in milliseconds."""

from dataclasses import dataclass


def hero_max_hp(level: int) -> int:
    if level < 1:
        raise ValueError("level must be positive")
    return 100 + 10 * (level - 1)


@dataclass(frozen=True)
class TurnResult:
    player_hp: int
    monster_hp: int
    damage_dealt: int
    damage_taken: int
    status: str


def resolve_turn(player_hp, monster_hp, correct, response_ms, monster_attack) -> TurnResult:
    if min(player_hp, monster_hp) <= 0 or min(response_ms, monster_attack) < 0:
        raise ValueError("a turn requires living combatants and nonnegative time/attack")
    dealt = (30 if response_ms <= 6000 else 20) if correct else 0
    taken = 0 if correct else monster_attack
    player_hp, monster_hp = max(0, player_hp - taken), max(0, monster_hp - dealt)
    status = "won" if monster_hp == 0 else "lost" if player_hp == 0 else "active"
    return TurnResult(player_hp, monster_hp, dealt, taken, status)


def add_xp(level: int, xp: int, reward: int) -> tuple[int, int]:
    if level < 1 or min(xp, reward) < 0:
        raise ValueError("level must be positive; XP and reward must be nonnegative")
    xp += reward
    while xp >= level * 100:
        xp -= level * 100
        level += 1
    return level, xp
