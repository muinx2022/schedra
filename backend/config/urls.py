"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework.routers import DefaultRouter

from campaigns.views import CampaignViewSet
from analytics.views import AnalyticsViewSet
from ideas.views import IdeaViewSet
from interactions.views import InboxCommunityPostCommentView, InboxCommunityPostDetailView, InboxCommunityPostsView, InboxSyncView, InboxThreadViewSet
from media_library.views import MediaAssetViewSet
from publishing.views import PostViewSet
from social.views import SocialAccountViewSet, SocialConnectionViewSet

router = DefaultRouter()
router.register("analytics", AnalyticsViewSet, basename="analytics")
router.register("campaigns", CampaignViewSet, basename="campaign")
router.register("ideas", IdeaViewSet, basename="idea")
router.register(r"inbox/threads", InboxThreadViewSet, basename="inbox-thread")
router.register("media", MediaAssetViewSet, basename="media")
router.register("connections", SocialConnectionViewSet, basename="connection")
router.register("accounts", SocialAccountViewSet, basename="social-account")
router.register("posts", PostViewSet, basename="post")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("staff/", include("back_office.urls")),
    path("health/", lambda _request: JsonResponse({"ok": True})),
    path("api/auth/", include("accounts.urls")),
    path("api/inbox/sync/", InboxSyncView.as_view()),
    path("api/inbox/community/<uuid:account_id>/posts/", InboxCommunityPostsView.as_view()),
    path("api/inbox/community/<uuid:account_id>/posts/<str:external_object_id>/", InboxCommunityPostDetailView.as_view()),
    path("api/inbox/community/<uuid:account_id>/posts/<str:external_object_id>/comment/", InboxCommunityPostCommentView.as_view()),
    path("api/", include(router.urls)),
]

media_prefix = (settings.MEDIA_URL or "/media/").lstrip("/")
if media_prefix:
    urlpatterns += [
        re_path(
            rf"^{media_prefix}(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]
