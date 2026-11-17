"""Atomic battle actions. Lock player before battle everywhere to serialize rewards."""

from random import Random

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.accounts.models import Player

from . import rules
from .generator import generate_question
from .models import Battle, Monster, Question


def unlocked(player, monster):
    # This slice supports Stage 1 only; later stages arrive with S3-1.
    if monster.stage.order != 1:
        return False
    previous = (
        Monster.objects.filter(stage=monster.stage, order__lt=monster.order)
        .order_by("-order")
        .first()
    )
    return (
        previous is None
        or Battle.objects.filter(player=player, monster=previous, status=Battle.Status.WON).exists()
    )


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
