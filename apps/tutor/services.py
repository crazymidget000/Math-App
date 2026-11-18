from django.db import transaction

from apps.game.models import Question

from . import client
from .models import HintRequest


@transaction.atomic
def hint_for_question(question):
    # Lock only the answered question, not the battle or next question. Repeated clicks
    # share one result without blocking the player's next answer during the AI call.
    question = Question.objects.select_for_update().get(pk=question.pk)
    saved = HintRequest.objects.filter(question=question).first()
    if saved is not None:
        return saved
    hint, status = client.request_hint(question)
    return HintRequest.objects.create(question=question, response_json=hint, status=status)
