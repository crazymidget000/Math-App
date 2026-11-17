from django.db import models


class Stage(models.Model):
    order = models.PositiveIntegerField(unique=True)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    operation = models.CharField(max_length=5)

    def __str__(self):
        return self.name


class Monster(models.Model):
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="monsters")
    order = models.PositiveIntegerField()
    name = models.CharField(max_length=80)
    emoji = models.CharField(max_length=10, default="👾")
    max_hp = models.PositiveIntegerField()
    attack = models.PositiveIntegerField(default=15)
    is_boss = models.BooleanField(default=False)
    xp_reward = models.PositiveIntegerField()
    coin_reward = models.PositiveIntegerField()
    question_params = models.JSONField()

    class Meta:
        ordering = ["stage__order", "order"]
        constraints = [models.UniqueConstraint(fields=["stage", "order"], name="monster_order")]

    def __str__(self):
        return self.name


class Battle(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        FLED = "fled", "Fled"

    player = models.ForeignKey("accounts.Player", on_delete=models.CASCADE, related_name="battles")
    monster = models.ForeignKey(Monster, on_delete=models.PROTECT)
    player_hp = models.PositiveIntegerField()
    player_max_hp = models.PositiveIntegerField()
    monster_hp = models.PositiveIntegerField()
    monster_max_hp = models.PositiveIntegerField()
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    xp_awarded = models.PositiveIntegerField(default=0)
    coins_awarded = models.PositiveIntegerField(default=0)
    leveled_up = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player"], condition=models.Q(status="active"), name="one_active_battle"
            )
        ]

    def __str__(self):
        return f"Battle {self.pk}: {self.status}"


class Question(models.Model):
    battle = models.ForeignKey(Battle, on_delete=models.CASCADE, related_name="questions")
    prompt = models.CharField(max_length=80)
    operand_a = models.PositiveIntegerField()
    operand_b = models.PositiveIntegerField()
    operation = models.CharField(max_length=5)
    correct_answer = models.IntegerField()
    player_answer = models.IntegerField(null=True)
    is_correct = models.BooleanField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True)
    response_ms = models.PositiveIntegerField(null=True)
    damage_dealt = models.PositiveIntegerField(default=0)
    damage_taken = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["battle"],
                condition=models.Q(answered_at__isnull=True),
                name="one_unanswered_question",
            )
        ]

    def __str__(self):
        return self.prompt
