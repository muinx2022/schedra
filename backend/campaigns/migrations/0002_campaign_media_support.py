import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="campaign",
            name="source_media_type",
            field=models.CharField(
                choices=[("none", "No media"), ("video", "Video"), ("images", "Images")],
                default="none",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="campaign",
            name="source_video",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="campaigns",
                to="media_library.mediaasset",
            ),
        ),
        migrations.CreateModel(
            name="CampaignMediaItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("order_index", models.PositiveIntegerField(default=0)),
                (
                    "campaign",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="media_items", to="campaigns.campaign"),
                ),
                (
                    "media_asset",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="campaign_items", to="media_library.mediaasset"),
                ),
            ],
            options={
                "ordering": ["order_index", "created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="campaignmediaitem",
            constraint=models.UniqueConstraint(fields=("campaign", "media_asset"), name="campaign_media_unique_asset"),
        ),
        migrations.AddConstraint(
            model_name="campaignmediaitem",
            constraint=models.UniqueConstraint(fields=("campaign", "order_index"), name="campaign_media_unique_order"),
        ),
    ]
