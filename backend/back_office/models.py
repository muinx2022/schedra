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
        help_text="Comma-separated scopes for Facebook Page OAuth. Keep Instagram scopes in the dedicated Instagram field.",
    )
    meta_graph_base_url = models.URLField(blank=True)
    meta_auth_base_url = models.URLField(blank=True)

    instagram_app_id = models.CharField(max_length=255, blank=True)
    instagram_app_secret_enc = models.TextField(blank=True)
    instagram_scopes = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated scopes for the standalone Instagram OAuth flow.",
    )
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


class AppMailSettings(models.Model):
    """Singleton (pk=1): app-level mail delivery and auth URL settings."""

    site_name = models.CharField(max_length=120, blank=True, default="Social Man")
    from_name = models.CharField(max_length=120, blank=True)
    from_email = models.EmailField(blank=True)
    reply_to_email = models.EmailField(blank=True)
    frontend_base_url = models.URLField(blank=True, help_text="Public app URL, e.g. https://socialman.com")
    password_reset_path = models.CharField(max_length=160, default="/reset-password")
    send_welcome_email = models.BooleanField(default=True)
    send_password_reset_email = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "App mail settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls) -> "AppMailSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


AUTH_EMAIL_TEMPLATE_DEFAULTS = {
    "welcome": {
        "name": "Welcome email",
        "description": (
            "Sent right after a new workspace owner registers. "
            "Available variables: {{ site_name }}, {{ first_name }}, {{ full_name }}, "
            "{{ email }}, {{ workspace_name }}, {{ login_url }}."
        ),
        "subject": "Welcome to {{ site_name }}, {{ first_name|default:full_name }}",
        "text_body": (
            "Hi {{ first_name|default:full_name }},\n\n"
            "Your workspace {{ workspace_name }} is ready.\n"
            "You can sign in here: {{ login_url }}\n\n"
            "If you did not create this account, you can ignore this email.\n\n"
            "{{ site_name }}"
        ),
        "html_body": (
            "<p>Hi {{ first_name|default:full_name }},</p>"
            "<p>Your workspace <strong>{{ workspace_name }}</strong> is ready.</p>"
            "<p><a href=\"{{ login_url }}\">Sign in to {{ site_name }}</a></p>"
            "<p>If you did not create this account, you can ignore this email.</p>"
            "<p>{{ site_name }}</p>"
        ),
    },
    "password_reset": {
        "name": "Password reset email",
        "description": (
            "Sent when a user requests a password reset. "
            "Available variables: {{ site_name }}, {{ first_name }}, {{ full_name }}, "
            "{{ email }}, {{ reset_url }}, {{ expires_in_minutes }}."
        ),
        "subject": "Reset your {{ site_name }} password",
        "text_body": (
            "Hi {{ first_name|default:full_name }},\n\n"
            "We received a request to reset the password for {{ email }}.\n"
            "Use this link to choose a new password:\n"
            "{{ reset_url }}\n\n"
            "This link expires in {{ expires_in_minutes }} minutes.\n"
            "If you did not request a password reset, you can ignore this email.\n\n"
            "{{ site_name }}"
        ),
        "html_body": (
            "<p>Hi {{ first_name|default:full_name }},</p>"
            "<p>We received a request to reset the password for <strong>{{ email }}</strong>.</p>"
            "<p><a href=\"{{ reset_url }}\">Choose a new password</a></p>"
            "<p>This link expires in {{ expires_in_minutes }} minutes.</p>"
            "<p>If you did not request a password reset, you can ignore this email.</p>"
            "<p>{{ site_name }}</p>"
        ),
    },
}


class AuthEmailTemplate(models.Model):
    class TemplateKey(models.TextChoices):
        WELCOME = "welcome", "Welcome email"
        PASSWORD_RESET = "password_reset", "Password reset email"

    key = models.CharField(max_length=64, choices=TemplateKey.choices, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=255)
    text_body = models.TextField(blank=True)
    html_body = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Auth email template"
        verbose_name_plural = "Auth email templates"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def load(cls, key: str) -> "AuthEmailTemplate":
        defaults = AUTH_EMAIL_TEMPLATE_DEFAULTS[key]
        obj, created = cls.objects.get_or_create(key=key, defaults=defaults)
        if created:
            return obj

        changed = False
        if not obj.name:
            obj.name = defaults["name"]
            changed = True
        if not obj.description:
            obj.description = defaults["description"]
            changed = True
        if not obj.subject:
            obj.subject = defaults["subject"]
            changed = True
        if not obj.text_body:
            obj.text_body = defaults["text_body"]
            changed = True
        if not obj.html_body:
            obj.html_body = defaults["html_body"]
            changed = True
        if changed:
            obj.save(update_fields=["name", "description", "subject", "text_body", "html_body", "updated_at"])
        return obj

    @classmethod
    def ensure_defaults(cls) -> list["AuthEmailTemplate"]:
        return [cls.load(key) for key in AUTH_EMAIL_TEMPLATE_DEFAULTS]
