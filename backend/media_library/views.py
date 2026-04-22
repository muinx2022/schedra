from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from .cleanup import delete_media_asset_file, get_media_asset_reference_summary
from .models import MediaAsset
from .serializers import MediaAssetSerializer


def _is_svg_upload(file_obj) -> bool:
    try:
        original_position = file_obj.tell()
    except Exception:
        original_position = None

    try:
        header = file_obj.read(512)
    finally:
        if original_position is not None:
            file_obj.seek(original_position)
        else:
            try:
                file_obj.seek(0)
            except Exception:
                pass

    if isinstance(header, str):
        sample = header.lower()
    else:
        sample = header.decode("utf-8", "ignore").lower()
    return "<svg" in sample


class MediaAssetViewSet(viewsets.ModelViewSet):
    serializer_class = MediaAssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MediaAsset.objects.filter(workspace=self.request.user.workspace).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        content_type = getattr(file_obj, "content_type", "") or "application/octet-stream"
        if not (content_type.startswith("image/") or content_type.startswith("video/")):
            return Response({"detail": "Only image and video uploads are supported."}, status=status.HTTP_400_BAD_REQUEST)
        if content_type.startswith("image/") and _is_svg_upload(file_obj):
            return Response(
                {"detail": "SVG uploads are not supported for social publishing. Export this asset as PNG or JPG first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        title = request.data.get("title") or file_obj.name

        # Keep upload URLs on the app's own domain so provider pull URLs can use a verified prefix.
        asset = MediaAsset.objects.create(
            workspace=request.user.workspace,
            uploaded_by=request.user,
            file=file_obj,
            title=title,
            file_name=file_obj.name,
            content_type=content_type,
            size_bytes=file_obj.size,
            storage_backend="local",
            storage_key="",
        )
        asset.storage_key = asset.file.name
        asset.save(update_fields=["storage_key"])

        serializer = MediaAssetSerializer(asset, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        asset = self.get_object()
        references = get_media_asset_reference_summary(asset)
        if references["total"] > 0:
            return Response(
                {
                    "detail": "This media asset is still used by posts or campaigns. Remove those references before deleting it.",
                    "references": references,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        delete_media_asset_file(asset)
        asset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
