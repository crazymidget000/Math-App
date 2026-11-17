from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import AnswerForm
from .models import Battle, Monster


@login_required
def play(request):
    player = getattr(request.user, "player", None)
    monsters = list(Monster.objects.filter(stage__order=1).select_related("stage"))
    defeated = set(
        Battle.objects.filter(player=player, status="won").values_list("monster_id", flat=True)
    )
    for monster in monsters:
        monster.unlocked = player is not None and services.unlocked(player, monster)
        monster.defeated = monster.pk in defeated
    active = Battle.objects.filter(player=player, status="active").first()
    return render(request, "game/play.html", {"monsters": monsters, "active": active})


def _render_battle(request, battle, form=None):
    question = battle.questions.filter(answered_at__isnull=True).first()
    last = battle.questions.filter(answered_at__isnull=False).order_by("-pk").first()
    if form is None and question:
        form = AnswerForm(initial={"question_id": question.pk})
    template = "game/battle.html"
    if request.headers.get("HX-Request") == "true":
        template = "game/_battle_state.html"
    return render(
        request, template, {"battle": battle, "question": question, "last": last, "form": form}
    )


@login_required
@require_POST
def start(request, monster_id):
    battle = services.start_battle(request.user, monster_id)
    return redirect("battle", battle_id=battle.pk)


@login_required
def battle_detail(request, battle_id):
    battle = get_object_or_404(
        Battle.objects.select_related("monster", "player"), pk=battle_id, player__user=request.user
    )
    return _render_battle(request, battle)


@login_required
@require_POST
def answer(request, battle_id):
    battle = get_object_or_404(Battle, pk=battle_id, player__user=request.user)
    form = AnswerForm(request.POST)
    if not form.is_valid():
        return _render_battle(request, battle, form)
    battle = services.answer_question(
        request.user, battle_id, form.cleaned_data["question_id"], form.cleaned_data["answer"]
    )
    if request.headers.get("HX-Request") == "true":
        return _render_battle(request, battle)
    return redirect("battle", battle_id=battle.pk)


@login_required
@require_POST
def flee(request, battle_id):
    services.flee_battle(request.user, battle_id)
    return redirect("play")
