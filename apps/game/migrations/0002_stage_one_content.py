from django.db import migrations


def seed_stage_one(apps, schema_editor):
    alias = schema_editor.connection.alias
    Stage = apps.get_model("game", "Stage")
    Monster = apps.get_model("game", "Monster")
    stage, _ = Stage.objects.using(alias).get_or_create(
        order=1, defaults={"slug": "addition-meadow", "name": "Addition Meadow", "operation": "add"}
    )
    monsters = [
        ("Slime", "🟢", 60, 15, 40, 10, {"op": "add", "max_sum": 10}),
        ("Goblin", "👺", 80, 15, 50, 15, {"op": "add", "max_sum": 20}),
        ("Troll", "👹", 100, 15, 60, 20, {"op": "add", "a_range": [10, 99], "b_range": [1, 9]}),
        ("Meadow Dragon", "🐉", 140, 20, 100, 40,
         {"op": "add", "a_range": [10, 99], "b_range": [10, 99], "max_sum": 100}),
    ]
    for order, (name, emoji, hp, attack, xp, coins, params) in enumerate(monsters, 1):
        Monster.objects.using(alias).get_or_create(stage=stage, order=order, defaults={
            "name": name, "emoji": emoji, "max_hp": hp, "attack": attack,
            "xp_reward": xp, "coin_reward": coins, "question_params": params,
            "is_boss": order == 4,
        })


class Migration(migrations.Migration):
    dependencies = [("game", "0001_initial")]
    operations = [migrations.RunPython(seed_stage_one, migrations.RunPython.noop)]
