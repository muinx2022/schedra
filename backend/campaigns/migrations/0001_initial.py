from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("media_library", "0003_alter_mediaasset_file"),
        ("publishing", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Campaign",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=200)),
                ("source_file", models.FileField(upload_to="campaign_sources/")),
                ("source_file_type", models.CharField(max_length=16)),
                ("source_text", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("uploaded", "Uploaded"), ("generated", "Generated"), ("drafted", "Drafted"), ("failed", "Failed")],
                        default="uploaded",
                        max_length=16,
                    ),
                ),
                ("segment_count", models.PositiveIntegerField(default=0)),
                ("total_video_duration_seconds", models.PositiveIntegerField(default=0)),
                (
                    "author",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="campaigns", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "source_video",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="campaigns", to="media_library.mediaasset"),
                ),
                (
                    "workspace",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="campaigns", to="accounts.workspace"),
                ),
            ],
            options={"ordering": ["-updated_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="CampaignSegment",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("order_index", models.PositiveIntegerField()),
                ("raw_text", models.TextField()),
                ("caption_text", models.TextField()),
                ("start_seconds", models.PositiveIntegerField(default=0)),
                ("end_seconds", models.PositiveIntegerField(default=0)),
                (
                    "status",
                    models.CharField(choices=[("generated", "Generated"), ("drafted", "Drafted")], default="generated", max_length=16),
                ),
                (
                    "campaign",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="segments", to="campaigns.campaign"),
                ),
                (
                    "draft_post",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="campaign_segments", to="publishing.post"),
                ),
            ],
            options={"ordering": ["order_index", "created_at"]},
        ),
        migrations.AddConstraint(
            model_name="campaignsegment",
            constraint=models.UniqueConstraint(fields=("campaign", "order_index"), name="campaign_segment_unique_order"),
        ),
    ]
