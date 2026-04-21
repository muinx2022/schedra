from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass
class UploadResult:
    storage_key: str   # relative path for local, public_id for cloudinary, s3 key
    url: str           # full accessible URL
    backend: str       # "local" | "cloudinary" | "s3"
    metadata: dict


class StorageBackend(ABC):
    backend_id: str

    @abstractmethod
    def upload(self, file_obj, filename: str, content_type: str) -> UploadResult:
        """Upload a file and return an UploadResult."""
        ...

    @abstractmethod
    def delete(self, storage_key: str, content_type: str = "") -> None:
        """Delete a file by its storage key."""
        ...

    @abstractmethod
    def get_url(self, storage_key: str, content_type: str = "") -> str:
        """Return the public URL for a storage key."""
        ...


class LocalStorageBackend(StorageBackend):
    """Stores files via Django's default MEDIA_ROOT / ImageField."""

    backend_id = "local"

    def upload(self, file_obj, filename: str, content_type: str) -> UploadResult:
        raise NotImplementedError("Local backend delegates to Django ImageField — use the serializer directly.")

    def delete(self, storage_key: str, content_type: str = "") -> None:
        from django.core.files.storage import default_storage
        if default_storage.exists(storage_key):
            default_storage.delete(storage_key)

    def get_url(self, storage_key: str, content_type: str = "") -> str:
        from django.core.files.storage import default_storage
        return default_storage.url(storage_key)


class CloudinaryBackend(StorageBackend):
    """Uploads files to Cloudinary via signed upload (API Key + Secret)."""

    backend_id = "cloudinary"
    _api_base = "https://api.cloudinary.com/v1_1"

    def __init__(
        self,
        cloud_name: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
    ):
        self.cloud_name = cloud_name if cloud_name is not None else os.getenv("CLOUDINARY_CLOUD_NAME", "")
        self.api_key = api_key if api_key is not None else os.getenv("CLOUDINARY_API_KEY", "")
        self.api_secret = api_secret if api_secret is not None else os.getenv("CLOUDINARY_API_SECRET", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.cloud_name and self.api_key and self.api_secret)

    def _resource_type(self, content_type: str) -> str:
        if (content_type or "").startswith("video/"):
            return "video"
        return "image"

    def _sign(self, params: dict) -> str:
        pairs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return hashlib.sha1((pairs + self.api_secret).encode()).hexdigest()

    def _multipart_body(self, fields: dict, file_data: bytes, filename: str, content_type: str):
        boundary = "----CloudinaryFormBoundary"
        parts = []
        for key, value in fields.items():
            parts.append(
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"{key}\"\r\n\r\n"
                f"{value}\r\n".encode()
            )
        parts.append(
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n".encode()
            + file_data + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode())
        return b"".join(parts), f"multipart/form-data; boundary={boundary}"

    def upload(self, file_obj, filename: str, content_type: str) -> UploadResult:
        if not self.is_configured:
            raise RuntimeError(
                "Cloudinary not configured. Set credentials in Back Office → Settings → Media or env vars."
            )

        ts = int(time.time())
        sign_params = {"timestamp": ts}
        signature = self._sign(sign_params)

        fields = {
            "api_key": self.api_key,
            "timestamp": str(ts),
            "signature": signature,
        }

        file_data = file_obj.read() if hasattr(file_obj, "read") else file_obj
        body, content_type_header = self._multipart_body(fields, file_data, filename, content_type)

        resource_type = self._resource_type(content_type)
        url = f"{self._api_base}/{self.cloud_name}/{resource_type}/upload"
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", content_type_header)

        try:
            with urlopen(req) as resp:
                result = json.loads(resp.read().decode())
        except Exception as e:
            import urllib.error
            if isinstance(e, urllib.error.HTTPError):
                raise RuntimeError(f"Cloudinary upload failed: {e.read().decode()}") from e
            raise

        return UploadResult(
            storage_key=result["public_id"],
            url=result["secure_url"],
            backend=self.backend_id,
            metadata={"width": result.get("width"), "height": result.get("height"), "format": result.get("format")},
        )

    def delete(self, storage_key: str, content_type: str = "") -> None:
        if not self.is_configured:
            return
        ts = int(time.time())
        sign_params = {"public_id": storage_key, "timestamp": ts}
        signature = self._sign(sign_params)
        fields = {
            "api_key": self.api_key,
            "timestamp": str(ts),
            "signature": signature,
            "public_id": storage_key,
        }
        body, ct = self._multipart_body(fields, b"", "", "")
        resource_type = self._resource_type(content_type)
        url = f"{self._api_base}/{self.cloud_name}/{resource_type}/destroy"
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", ct)
        try:
            urlopen(req)
        except Exception:
            pass

    def get_url(self, storage_key: str, content_type: str = "") -> str:
        resource_type = self._resource_type(content_type)
        return f"https://res.cloudinary.com/{self.cloud_name}/{resource_type}/upload/{storage_key}"


class S3StorageBackend(StorageBackend):
    backend_id = "s3"

    def __init__(
        self,
        bucket: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        prefix: str = "",
        public_base_url: str = "",
        endpoint_url: str = "",
    ):
        self.bucket = bucket
        self.region = region
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.prefix = (prefix or "").strip("/")
        self.public_base_url = (public_base_url or "").rstrip("/")
        self.endpoint_url = (endpoint_url or "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.bucket and self.region and self.access_key_id and self.secret_access_key)

    def _client(self):
        try:
            import boto3  # type: ignore
        except ImportError as e:
            raise RuntimeError("S3 backend requires boto3. Install with: pip install boto3") from e

        kwargs = {
            "region_name": self.region,
            "aws_access_key_id": self.access_key_id,
            "aws_secret_access_key": self.secret_access_key,
        }
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        return boto3.client("s3", **kwargs)

    def _object_key(self, filename: str) -> str:
        stem = f"{uuid.uuid4().hex}_{filename}"
        if self.prefix:
            return f"{self.prefix}/{stem}"
        return stem

    def upload(self, file_obj, filename: str, content_type: str) -> UploadResult:
        if not self.is_configured:
            raise RuntimeError("S3 is not fully configured (bucket, region, access key, secret).")

        client = self._client()
        key = self._object_key(filename)
        body = file_obj.read() if hasattr(file_obj, "read") else file_obj
        extra = {"ContentType": content_type} if content_type else {}
        client.put_object(Bucket=self.bucket, Key=key, Body=body, **extra)
        url = self.get_url(key)
        return UploadResult(
            storage_key=key,
            url=url,
            backend=self.backend_id,
            metadata={},
        )

    def delete(self, storage_key: str, content_type: str = "") -> None:
        if not self.is_configured:
            return
        try:
            self._client().delete_object(Bucket=self.bucket, Key=storage_key)
        except Exception:
            pass

    def get_url(self, storage_key: str, content_type: str = "") -> str:
        if not self.bucket or not self.region:
            return ""
        if self.public_base_url:
            return f"{self.public_base_url}/{quote(storage_key, safe='/')}"
        hosting = f"{self.bucket}.s3.{self.region}.amazonaws.com"
        return f"https://{hosting}/{quote(storage_key, safe='/')}"


def _media_settings():
    try:
        from back_office.models import MediaUploadSettings

        return MediaUploadSettings.objects.filter(pk=1).first()
    except Exception:
        return None


def _cloudinary_from_db_or_env():
    from common.security import decrypt_value

    s = _media_settings()
    base = CloudinaryBackend()
    if not s or (s.upload_provider or "").lower() != "cloudinary":
        return base

    secret = decrypt_value(s.cloudinary_api_secret_enc) if s.cloudinary_api_secret_enc else base.api_secret
    return CloudinaryBackend(
        cloud_name=s.cloudinary_cloud_name or base.cloud_name,
        api_key=s.cloudinary_api_key or base.api_key,
        api_secret=secret or base.api_secret,
    )


def _s3_from_db():
    s = _media_settings()
    if not s:
        return None
    from common.security import decrypt_value

    secret = decrypt_value(s.s3_secret_access_key_enc) if s.s3_secret_access_key_enc else ""
    if not (s.s3_bucket and s.s3_region and s.s3_access_key_id and secret):
        return None
    return S3StorageBackend(
        bucket=s.s3_bucket,
        region=s.s3_region,
        access_key_id=s.s3_access_key_id,
        secret_access_key=secret,
        prefix=s.s3_prefix or "",
        public_base_url=s.s3_public_base_url or "",
        endpoint_url=s.s3_endpoint_url or "",
    )


def _active_provider() -> str:
    s = _media_settings()
    if s:
        return (s.upload_provider or "local").lower()
    return os.getenv("STORAGE_BACKEND", "local").lower()


def get_storage_backend() -> StorageBackend:
    """Backend used for new uploads (DB settings override env when set)."""
    p = _active_provider()
    if p == "cloudinary":
        return _cloudinary_from_db_or_env()
    if p == "s3":
        backend = _s3_from_db()
        if backend and backend.is_configured:
            return backend
        raise RuntimeError("S3 is selected but credentials are missing. Complete Settings → Media.")
    return LocalStorageBackend()


def get_backend_by_id(backend_id: str) -> StorageBackend:
    """Resolve credentials for an existing asset (same rules as active config)."""
    bid = (backend_id or "local").lower()
    if bid == "cloudinary":
        return _cloudinary_from_db_or_env()
    if bid == "s3":
        backend = _s3_from_db()
        if backend and backend.is_configured:
            return backend
        return S3StorageBackend(
            bucket="",
            region="",
            access_key_id="",
            secret_access_key="",
        )
    return LocalStorageBackend()
    def _resource_type(self, content_type: str) -> str:
        if (content_type or "").startswith("video/"):
            return "video"
        return "image"
