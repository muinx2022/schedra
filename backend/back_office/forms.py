from django import forms

from common.security import encrypt_value

from .models import MediaUploadSettings, SocialProviderSettings


class MediaUploadSettingsForm(forms.ModelForm):
    cloudinary_api_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "form-control", "autocomplete": "new-password"},
        ),
        help_text="Leave blank to keep the current secret.",
    )
    s3_secret_access_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "form-control", "autocomplete": "new-password"},
        ),
        help_text="Leave blank to keep the current secret.",
    )

    class Meta:
        model = MediaUploadSettings
        fields = [
            "upload_provider",
            "local_public_base_url",
            "cloudinary_cloud_name",
            "cloudinary_api_key",
            "s3_bucket",
            "s3_region",
            "s3_prefix",
            "s3_access_key_id",
            "s3_public_base_url",
            "s3_endpoint_url",
        ]
        widgets = {
            "upload_provider": forms.Select(attrs={"class": "form-select"}),
            "local_public_base_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "cloudinary_cloud_name": forms.TextInput(attrs={"class": "form-control"}),
            "cloudinary_api_key": forms.TextInput(attrs={"class": "form-control"}),
            "s3_bucket": forms.TextInput(attrs={"class": "form-control"}),
            "s3_region": forms.TextInput(attrs={"class": "form-control", "placeholder": "ap-southeast-1"}),
            "s3_prefix": forms.TextInput(attrs={"class": "form-control"}),
            "s3_access_key_id": forms.TextInput(attrs={"class": "form-control"}),
            "s3_public_base_url": forms.URLInput(attrs={"class": "form-control"}),
            "s3_endpoint_url": forms.URLInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.cloudinary_api_secret_enc:
                self.fields["cloudinary_api_secret"].help_text = (
                    "Secret is set. Leave blank to keep it, or enter a new value to replace."
                )
            if self.instance.s3_secret_access_key_enc:
                self.fields["s3_secret_access_key"].help_text = (
                    "Secret is set. Leave blank to keep it, or enter a new value to replace."
                )

    def save(self, commit=True):
        obj = super().save(commit=False)
        secret = self.cleaned_data.get("cloudinary_api_secret") or ""
        if secret.strip():
            obj.cloudinary_api_secret_enc = encrypt_value(secret.strip())
        s3_secret = self.cleaned_data.get("s3_secret_access_key") or ""
        if s3_secret.strip():
            obj.s3_secret_access_key_enc = encrypt_value(s3_secret.strip())
        if commit:
            obj.save()
        return obj


class SocialProviderSettingsForm(forms.ModelForm):
    meta_app_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "form-control", "autocomplete": "new-password"},
        ),
        help_text="Leave blank to keep the current secret.",
    )
    instagram_app_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "form-control", "autocomplete": "new-password"},
        ),
        help_text="Leave blank to keep the current secret.",
    )
    x_client_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "form-control", "autocomplete": "new-password"},
        ),
        help_text="Leave blank to keep the current secret.",
    )
    tiktok_client_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "form-control", "autocomplete": "new-password"},
        ),
        help_text="Leave blank to keep the current secret.",
    )
    linkedin_client_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "form-control", "autocomplete": "new-password"},
        ),
        help_text="Leave blank to keep the current secret.",
    )
    youtube_client_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "form-control", "autocomplete": "new-password"},
        ),
        help_text="Leave blank to keep the current secret.",
    )
    pinterest_app_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "form-control", "autocomplete": "new-password"},
        ),
        help_text="Leave blank to keep the current secret.",
    )

    class Meta:
        model = SocialProviderSettings
        fields = [
            "meta_app_id",
            "meta_scopes",
            "meta_graph_base_url",
            "meta_auth_base_url",
            "instagram_app_id",
            "instagram_scopes",
            "instagram_graph_base_url",
            "instagram_auth_base_url",
            "instagram_token_base_url",
            "x_client_id",
            "x_scopes",
            "tiktok_client_key",
            "tiktok_scopes",
            "linkedin_client_id",
            "linkedin_scopes",
            "youtube_client_id",
            "youtube_scopes",
            "pinterest_app_id",
            "pinterest_scopes",
        ]
        widgets = {
            "meta_app_id": forms.TextInput(attrs={"class": "form-control"}),
            "meta_scopes": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "pages_show_list,business_management,pages_manage_posts,pages_read_engagement,pages_manage_metadata,pages_read_user_content,read_insights,instagram_basic,instagram_content_publish,instagram_manage_insights,instagram_manage_comments",
                }
            ),
            "meta_graph_base_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://graph.facebook.com/v23.0"}),
            "meta_auth_base_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://www.facebook.com/v23.0/dialog/oauth"}),
            "instagram_app_id": forms.TextInput(attrs={"class": "form-control"}),
            "instagram_scopes": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "instagram_business_basic,instagram_business_content_publish",
                }
            ),
            "instagram_graph_base_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://graph.instagram.com"}),
            "instagram_auth_base_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://www.instagram.com/oauth/authorize"}),
            "instagram_token_base_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://api.instagram.com/oauth/access_token"}),
            "x_client_id": forms.TextInput(attrs={"class": "form-control"}),
            "x_scopes": forms.TextInput(attrs={"class": "form-control", "placeholder": "tweet.read tweet.write users.read offline.access"}),
            "tiktok_client_key": forms.TextInput(attrs={"class": "form-control"}),
            "tiktok_scopes": forms.TextInput(attrs={"class": "form-control", "placeholder": "user.info.basic,video.publish"}),
            "linkedin_client_id": forms.TextInput(attrs={"class": "form-control"}),
            "linkedin_scopes": forms.TextInput(attrs={"class": "form-control", "placeholder": "openid,profile,email,w_member_social"}),
            "youtube_client_id": forms.TextInput(attrs={"class": "form-control"}),
            "youtube_scopes": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://www.googleapis.com/auth/youtube.upload,https://www.googleapis.com/auth/youtube.readonly",
                }
            ),
            "pinterest_app_id": forms.TextInput(attrs={"class": "form-control"}),
            "pinterest_scopes": forms.TextInput(attrs={"class": "form-control", "placeholder": "boards:read,pins:read,pins:write"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["meta_scopes"].help_text = (
                "Include publishing, insights, and comments scopes for Meta Page and Instagram Business sync."
            )
            if self.instance.meta_app_secret_enc:
                self.fields["meta_app_secret"].help_text = (
                    "Secret is set. Leave blank to keep it, or enter a new value to replace."
                )
            if self.instance.instagram_app_secret_enc:
                self.fields["instagram_app_secret"].help_text = (
                    "Secret is set. Leave blank to keep it, or enter a new value to replace."
                )
            if self.instance.x_client_secret_enc:
                self.fields["x_client_secret"].help_text = (
                    "Secret is set. Leave blank to keep it, or enter a new value to replace."
                )
            if self.instance.tiktok_client_secret_enc:
                self.fields["tiktok_client_secret"].help_text = (
                    "Secret is set. Leave blank to keep it, or enter a new value to replace."
                )
            if self.instance.linkedin_client_secret_enc:
                self.fields["linkedin_client_secret"].help_text = (
                    "Secret is set. Leave blank to keep it, or enter a new value to replace."
                )
            if self.instance.youtube_client_secret_enc:
                self.fields["youtube_client_secret"].help_text = (
                    "Secret is set. Leave blank to keep it, or enter a new value to replace."
                )
            if self.instance.pinterest_app_secret_enc:
                self.fields["pinterest_app_secret"].help_text = (
                    "Secret is set. Leave blank to keep it, or enter a new value to replace."
                )

    def save(self, commit=True):
        obj = super().save(commit=False)

        meta_secret = self.cleaned_data.get("meta_app_secret") or ""
        if meta_secret.strip():
            obj.meta_app_secret_enc = encrypt_value(meta_secret.strip())

        instagram_secret = self.cleaned_data.get("instagram_app_secret") or ""
        if instagram_secret.strip():
            obj.instagram_app_secret_enc = encrypt_value(instagram_secret.strip())

        x_secret = self.cleaned_data.get("x_client_secret") or ""
        if x_secret.strip():
            obj.x_client_secret_enc = encrypt_value(x_secret.strip())

        tiktok_secret = self.cleaned_data.get("tiktok_client_secret") or ""
        if tiktok_secret.strip():
            obj.tiktok_client_secret_enc = encrypt_value(tiktok_secret.strip())

        linkedin_secret = self.cleaned_data.get("linkedin_client_secret") or ""
        if linkedin_secret.strip():
            obj.linkedin_client_secret_enc = encrypt_value(linkedin_secret.strip())

        youtube_secret = self.cleaned_data.get("youtube_client_secret") or ""
        if youtube_secret.strip():
            obj.youtube_client_secret_enc = encrypt_value(youtube_secret.strip())

        pinterest_secret = self.cleaned_data.get("pinterest_app_secret") or ""
        if pinterest_secret.strip():
            obj.pinterest_app_secret_enc = encrypt_value(pinterest_secret.strip())

        if commit:
            obj.save()
        return obj

