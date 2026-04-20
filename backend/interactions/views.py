from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from social.models import SocialAccount

from .models import InteractionThread
from .serializers import (
    InboxSyncRequestSerializer,
    InteractionThreadDetailSerializer,
    InteractionThreadListSerializer,
    InteractionThreadWriteSerializer,
)
from .services import inbox_thread_queryset_for_workspace
from .tasks import sync_inbox_comments_workspace


class InboxThreadViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return inbox_thread_queryset_for_workspace(
            self.request.user.workspace,
            status_value=self.request.query_params.get("status") or None,
            account_id=self.request.query_params.get("account") or None,
            platform=self.request.query_params.get("platform") or None,
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return InteractionThreadDetailSerializer
        if self.action in {"partial_update", "update"}:
            return InteractionThreadWriteSerializer
        return InteractionThreadListSerializer

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(InteractionThreadDetailSerializer(instance).data)


class InboxSyncView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = InboxSyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account_id = serializer.validated_data.get("account")
        if account_id is not None:
            get_object_or_404(
                SocialAccount.objects.select_related("provider"),
                pk=account_id,
                workspace=request.user.workspace,
            )
        sync_inbox_comments_workspace.delay(str(request.user.workspace.id), str(account_id) if account_id else None)
        return Response(
            {
                "status": "queued",
                "account_id": str(account_id) if account_id else None,
            },
            status=status.HTTP_202_ACCEPTED,
        )
