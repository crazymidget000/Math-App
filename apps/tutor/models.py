from django.db import models


class HintRequest(models.Model):
    question = models.OneToOneField(
        "game.Question", on_delete=models.CASCADE, related_name="wizard_hint"
    )
    response_json = models.JSONField()
    status = models.CharField(max_length=8, choices=[("ok", "OK"), ("fallback", "Fallback")])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wizard hint for question {self.question_id}"
