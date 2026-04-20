from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ideas", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="idea",
            name="column",
            field=models.CharField(
                choices=[
                    ("unassigned", "Unassigned"),
                    ("inbox", "Inbox"),
                    ("planned", "Planned"),
                    ("ready", "Ready"),
                ],
                default="unassigned",
                max_length=32,
            ),
        ),
    ]
