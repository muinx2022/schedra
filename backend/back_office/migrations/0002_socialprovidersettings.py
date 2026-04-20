from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("back_office", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialProviderSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("meta_app_id", models.CharField(blank=True, max_length=255)),
                ("meta_app_secret_enc", models.TextField(blank=True)),
                ("meta_scopes", models.CharField(blank=True, help_text="Comma-separated scopes used for Meta OAuth.", max_length=500)),
                ("meta_graph_base_url", models.URLField(blank=True)),
                ("meta_auth_base_url", models.URLField(blank=True)),
                ("x_client_id", models.CharField(blank=True, max_length=255)),
                ("x_client_secret_enc", models.TextField(blank=True)),
                ("x_scopes", models.CharField(blank=True, max_length=500)),
                ("tiktok_client_key", models.CharField(blank=True, max_length=255)),
                ("tiktok_client_secret_enc", models.TextField(blank=True)),
                ("tiktok_scopes", models.CharField(blank=True, max_length=500)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Social provider settings",
            },
        ),
    ]
