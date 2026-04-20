from django.urls import path

from . import views

app_name = "back_office"

urlpatterns = [
    path("login/", views.StaffLoginView.as_view(), name="login"),
    path("logout/", views.staff_logout, name="logout"),
    path("settings/", views.BackOfficeSettingsView.as_view(), name="settings"),
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("<str:app_label>/<str:model_name>/", views.ModelListView.as_view(), name="model_list"),
    path("<str:app_label>/<str:model_name>/add/", views.ModelCreateView.as_view(), name="model_add"),
    path(
        "<str:app_label>/<str:model_name>/<path:pk>/edit/",
        views.ModelUpdateView.as_view(),
        name="model_edit",
    ),
    path(
        "<str:app_label>/<str:model_name>/<path:pk>/delete/",
        views.ModelDeleteView.as_view(),
        name="model_delete",
    ),
]

