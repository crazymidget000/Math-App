"""Atomic battle actions. Lock player before battle everywhere to serialize rewards."""

from random import Random

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.accounts.models import Player

from . import progression, rules
from .generator import generate_question
from .models import Battle, Monster, Question

# Stages whose questions the generator can already produce. Raise this in S3-1.
PLAYABLE_STAGE_LIMIT = 2


def progress_for(player):
    """Return (monsters, stages) with progression state attached.

    Two queries total, however many monsters there are. Each monster gets
    .state ("locked" / "unlocked" / "defeated"), .unlocked (can be battled now, which
    includes replaying a defeated monster) and .defeated. stages is a list of
    {"stage", "monsters", "open"} dicts.
    """
    monsters = list(Monster.objects.select_related("stage").order_by("stage__order", "order"))
    defeated = set()
    if player is not None:
        defeated = set(
            Battle.objects.filter(player=player, status=Battle.Status.WON).values_list(
                "monster_id", flat=True
            )
        )
    grouped = {}
    for monster in monsters:
        grouped.setdefault(monster.stage_id, []).append(monster)
    stage_lists = list(grouped.values())
    states = progression.monster_states(
        [[(m.pk, m.is_boss) for m in stage_monsters] for stage_monsters in stage_lists],
        defeated,
    )
    stages = []
    for stage_monsters in stage_lists:
        for monster in stage_monsters:
            state = states[monster.pk]
            if state == progression.UNLOCKED and monster.stage.order > PLAYABLE_STAGE_LIMIT:
                state = progression.LOCKED
            monster.state = state
            monster.unlocked = state in (progression.UNLOCKED, progression.DEFEATED)
            monster.defeated = state == progression.DEFEATED
        stages.append(
            {
                "stage": stage_monsters[0].stage,
                "monsters": stage_monsters,
                "open": any(m.state != progression.LOCKED for m in stage_monsters),
            }
        )
    return monsters, stages


def unlocked(player, monster):
    """True if the monster can be battled now: unlocked, or defeated and replayed."""
    monsters, _ = progress_for(player)
    return any(m.pk == monster.pk and m.unlocked for m in monsters)


def _next_question(battle):
    previous = battle.questions.order_by("-pk").first()
    rng = Random()
    for _ in range(100):
        q = generate_question(battle.monster.question_params, rng)
        if previous is None or q.prompt != previous.prompt:
            return Question.objects.create(
                battle=battle,
                prompt=q.prompt,
                operand_a=q.a,
                operand_b=q.b,
                operation=q.operation,
                correct_answer=q.answer,
            )
    raise ValueError("Monster configuration cannot supply a different question")


@transaction.atomic
def start_battle(user, monster_id):
    player = get_object_or_404(Player.objects.select_for_update(), user=user)
    monster = get_object_or_404(Monster.objects.select_related("stage"), pk=monster_id)
    if not unlocked(player, monster):
        raise Http404
    active = Battle.objects.filter(player=player, status=Battle.Status.ACTIVE).first()
    if active:
        return active
    hp = rules.hero_max_hp(player.level)
    battle = Battle.objects.create(
        player=player,
        monster=monster,
        player_hp=hp,
        player_max_hp=hp,
        monster_hp=monster.max_hp,
        monster_max_hp=monster.max_hp,
    )
    _next_question(battle)
    return battle


def _locked_battle(user, battle_id):
    player = get_object_or_404(Player.objects.select_for_update(), user=user)
    battle = get_object_or_404(Battle.objects.select_for_update(), pk=battle_id, player=player)
    return player, battle


@transaction.atomic
def answer_question(user, battle_id, question_id, answer):
    player, battle = _locked_battle(user, battle_id)
    question = get_object_or_404(Question, pk=question_id, battle=battle)
    # The submitted question ID makes stale forms and double-clicks idempotent.
    if battle.status != Battle.Status.ACTIVE or question.answered_at is not None:
        return battle
    now = timezone.now()
    question.player_answer = answer
    question.is_correct = answer == question.correct_answer
    question.response_ms = max(0, int((now - question.created_at).total_seconds() * 1000))
    turn = rules.resolve_turn(
        battle.player_hp,
        battle.monster_hp,
        question.is_correct,
        question.response_ms,
        battle.monster.attack,
    )
    question.damage_dealt, question.damage_taken = turn.damage_dealt, turn.damage_taken
    question.answered_at = now
    question.save()
    battle.player_hp, battle.monster_hp, battle.status = (
        turn.player_hp,
        turn.monster_hp,
        turn.status,
    )
    if battle.status != Battle.Status.ACTIVE:
        battle.ended_at = now
    if battle.status == Battle.Status.WON:
        battle.xp_awarded, battle.coins_awarded = (
            battle.monster.xp_reward,
            battle.monster.coin_reward,
        )
        old_level = player.level
        player.level, player.xp = rules.add_xp(player.level, player.xp, battle.xp_awarded)
        player.coins += battle.coins_awarded
        battle.leveled_up = player.level > old_level
        player.save(update_fields=["level", "xp", "coins", "updated_at"])
    battle.save()
    if battle.status == Battle.Status.ACTIVE:
        _next_question(battle)
    return battle


@transaction.atomic
def flee_battle(user, battle_id):
    _, battle = _locked_battle(user, battle_id)
    if battle.status == Battle.Status.ACTIVE:
        battle.status, battle.ended_at = Battle.Status.FLED, timezone.now()
        battle.save(update_fields=["status", "ended_at"])
    return battle
