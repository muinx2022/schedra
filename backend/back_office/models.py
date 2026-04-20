from django.db import models


class MediaUploadSettings(models.Model):
    """Singleton (pk=1): upload provider and credentials for media library."""

    class Provider(models.TextChoices):
        LOCAL = "local", "Local filesystem"
        CLOUDINARY = "cloudinary", "Cloudinary"
        S3 = "s3", "Amazon S3"

    upload_provider = models.CharField(
        max_length=32,
        choices=Provider.choices,
        default=Provider.LOCAL,
    )

    # Local — optional public base for absolute URLs (e.g. behind reverse proxy)
    local_public_base_url = models.URLField(blank=True, help_text="Optional, e.g. https://cdn.example.com")

    # Cloudinary
    cloudinary_cloud_name = models.CharField(max_length=255, blank=True)
    cloudinary_api_key = models.CharField(max_length=255, blank=True)
    cloudinary_api_secret_enc = models.TextField(blank=True)

    # S3-compatible
    s3_bucket = models.CharField(max_length=255, blank=True)
    s3_region = models.CharField(max_length=64, blank=True)
    s3_prefix = models.CharField(max_length=255, blank=True)
    s3_access_key_id = models.CharField(max_length=128, blank=True)
    s3_secret_access_key_enc = models.TextField(blank=True)
    s3_public_base_url = models.URLField(blank=True, help_text="Optional CDN or custom domain base URL")
    s3_endpoint_url = models.URLField(blank=True, help_text="Optional, for MinIO / custom endpoint")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Media upload settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls) -> "MediaUploadSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SocialProviderSettings(models.Model):
    """Singleton (pk=1): app-level credentials and defaults for social providers."""

    meta_app_id = models.CharField(max_length=255, blank=True)
    meta_app_secret_enc = models.TextField(blank=True)
    meta_scopes = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated scopes used for Meta OAuth.",
    )
    meta_graph_base_url = models.URLField(blank=True)
    meta_auth_base_url = models.URLField(blank=True)

    instagram_app_id = models.CharField(max_length=255, blank=True)
    instagram_app_secret_enc = models.TextField(blank=True)
    instagram_scopes = models.CharField(max_length=500, blank=True)
    instagram_graph_base_url = models.URLField(blank=True)
    instagram_auth_base_url = models.URLField(blank=True)
    instagram_token_base_url = models.URLField(blank=True)

    x_client_id = models.CharField(max_length=255, blank=True)
    x_client_secret_enc = models.TextField(blank=True)
    x_scopes = models.CharField(max_length=500, blank=True)

    tiktok_client_key = models.CharField(max_length=255, blank=True)
    tiktok_client_secret_enc = models.TextField(blank=True)
    tiktok_scopes = models.CharField(max_length=500, blank=True)

    linkedin_client_id = models.CharField(max_length=255, blank=True)
    linkedin_client_secret_enc = models.TextField(blank=True)
    linkedin_scopes = models.CharField(max_length=500, blank=True)

    youtube_client_id = models.CharField(max_length=255, blank=True)
    youtube_client_secret_enc = models.TextField(blank=True)
    youtube_scopes = models.CharField(max_length=500, blank=True)

    pinterest_app_id = models.CharField(max_length=255, blank=True)
    pinterest_app_secret_enc = models.TextField(blank=True)
    pinterest_scopes = models.CharField(max_length=500, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Social provider settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls) -> "SocialProviderSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
