from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from social.models import SocialAccount

from .serializers import AnalyticsQuerySerializer, AnalyticsSyncRequestSerializer, WorkspaceAnalyticsSerializer
from .services import build_workspace_analytics
from .tasks import sync_provider_insights_workspace


class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        query_serializer = AnalyticsQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        account = None
        account_id = query_serializer.validated_data.get("account")
        if account_id is not None:
            account = get_object_or_404(
                SocialAccount.objects.select_related("provider"),
                pk=account_id,
                workspace=request.user.workspace,
            )

        payload = build_workspace_analytics(
            request.user.workspace,
            range_key=query_serializer.validated_data.get("range", "30d"),
            account=account,
        )
        serializer = WorkspaceAnalyticsSerializer(payload)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="provider-sync")
    def provider_sync(self, request):
        serializer = AnalyticsSyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account_id = serializer.validated_data.get("account")
        if account_id is not None:
            get_object_or_404(
                SocialAccount.objects.select_related("provider"),
                pk=account_id,
                workspace=request.user.workspace,
            )

        sync_provider_insights_workspace.delay(str(request.user.workspace.id), str(account_id) if account_id else None)
        return Response(
            {
                "status": "queued",
                "account_id": str(account_id) if account_id else None,
            },
            status=status.HTTP_202_ACCEPTED,
        )
