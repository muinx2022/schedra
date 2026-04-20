from django.db import migrations, models


def forwards(apps, schema_editor):
    Idea = apps.get_model("ideas", "Idea")
    mapping = {
        "inbox": "todo",
        "planned": "in_progress",
        "ready": "done",
    }
    for old_value, new_value in mapping.items():
        Idea.objects.filter(column=old_value).update(column=new_value)


def backwards(apps, schema_editor):
    Idea = apps.get_model("ideas", "Idea")
    mapping = {
        "todo": "inbox",
        "in_progress": "planned",
        "done": "ready",
    }
    for old_value, new_value in mapping.items():
        Idea.objects.filter(column=old_value).update(column=new_value)


class Migration(migrations.Migration):
    dependencies = [
        ("ideas", "0002_alter_idea_column"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="idea",
            name="column",
            field=models.CharField(
                choices=[
                    ("unassigned", "Unassigned"),
                    ("todo", "Todo"),
                    ("in_progress", "In Progress"),
                    ("done", "Done"),
                ],
                default="unassigned",
                max_length=32,
            ),
        ),
    ]
