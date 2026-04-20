from django.conf import settings
from django.db import models
from urllib.parse import urljoin

from accounts.models import Workspace
from back_office.models import MediaUploadSettings
from common.models import BaseModel


class MediaAsset(BaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="media_assets")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="media_assets",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    # Local storage: file is populated, storage_key mirrors file.name
    file = models.FileField(upload_to="media_assets/", null=True, blank=True)
    # Cloudinary (or future backends): file is empty, storage_key holds public_id
    storage_backend = models.CharField(max_length=32, default="local")
    storage_key = models.CharField(max_length=500, blank=True)
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, default="image/jpeg")
    size_bytes = models.PositiveBigIntegerField(default=0)
    alt_text = models.CharField(max_length=255, blank=True)

    @property
    def kind(self) -> str:
        if (self.content_type or "").startswith("video/"):
            return "video"
        return "image"

    def get_file_url(self, request=None) -> str:
        if self.storage_backend in ("cloudinary", "s3"):
            from .storage import get_backend_by_id

            return get_backend_by_id(self.storage_backend).get_url(self.storage_key)
        # local
        if self.file:
            if request:
                return request.build_absolute_uri(self.file.url)
            return self.file.url
        return ""

    def get_public_file_url(self, request=None) -> str:
        """Return a public absolute URL suitable for provider-side media ingestion."""
        if self.storage_backend in ("cloudinary", "s3"):
            return self.get_file_url(request=request)

        if not self.file:
            return ""

        if request:
            return request.build_absolute_uri(self.file.url)

        media_settings = MediaUploadSettings.load()
        public_base = (media_settings.local_public_base_url or "").strip()
        if public_base:
            return urljoin(f"{public_base.rstrip('/')}/", self.file.url.lstrip("/"))

        raise ValueError(
            "Local media assets need a public base URL before they can be published to social providers. "
            "Set Media settings -> Local public base URL in staff settings."
        )
