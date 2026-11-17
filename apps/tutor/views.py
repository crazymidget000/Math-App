from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.game.models import Battle, Question

from .services import hint_for_question


class HintQuestionForm(forms.Form):
    question_id = forms.IntegerField(min_value=1, max_value=2**63 - 1)


@login_required
@require_POST
def hint(request, battle_id):
    battle = get_object_or_404(Battle, pk=battle_id, player__user=request.user)
    form = HintQuestionForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Choose a question to ask the wizard about.")
    question = get_object_or_404(
        Question,
        pk=form.cleaned_data["question_id"],
        battle=battle,
        is_correct=False,
        answered_at__isnull=False,
    )
    saved = hint_for_question(question)
    if request.headers.get("HX-Request") == "true":
        return render(request, "tutor/_hint.html", {"question": question, "hint": saved})
    return redirect(f"{reverse('battle', args=[battle.pk])}#wizard-hint-{question.pk}")
