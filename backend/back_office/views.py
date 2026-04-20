from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import logout as django_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.forms import modelform_factory
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.text import capfirst
from django.views import View
from django.views.generic import FormView, TemplateView

from .forms import AppMailSettingsForm, AuthEmailTemplateForm, MediaUploadSettingsForm, SocialProviderSettingsForm
from .models import (
    AUTH_EMAIL_TEMPLATE_DEFAULTS,
    AppMailSettings,
    AuthEmailTemplate,
    MediaUploadSettings,
    SocialProviderSettings,
)


@dataclass(frozen=True)
class ModelRef:
    app_label: str
    model_name: str  # lower-case model name in URLs
    verbose_name_plural: str


def _is_auto_or_uneditable_field(field: models.Field) -> bool:
    if getattr(field, "primary_key", False):
        return True
    if getattr(field, "auto_created", False):
        return True
    if getattr(field, "editable", True) is False:
        return True
    return False


def get_model_or_404(app_label: str, model_name: str) -> type[models.Model]:
    model = apps.get_model(app_label, model_name)
    if model is None:
        raise Http404("Model not found.")
    return model


def perm_codename(action: str, model: type[models.Model]) -> str:
    return f"{model._meta.app_label}.{action}_{model._meta.model_name}"


def staff_gate(request: HttpRequest) -> None:
    user = request.user
    if not user.is_authenticated:
        raise PermissionDenied
    if not user.is_staff:
        raise PermissionDenied


def list_registered_models_for_user(request: HttpRequest) -> dict[str, list[ModelRef]]:
    """
    Returns {app_label: [ModelRef...]} for models user can at least view.
    Excludes django/contrib internals by default, except your project apps.
    """
    staff_gate(request)
    user = request.user

    grouped: dict[str, list[ModelRef]] = {}
    for model in apps.get_models():
        app_label = model._meta.app_label

        # Skip Django internal apps to reduce noise (still adjustable later).
        if app_label.startswith("django"):
            continue
        if app_label in {"admin", "auth", "contenttypes", "sessions"}:
            continue

        if not user.has_perm(perm_codename("view", model)):
            continue

        grouped.setdefault(app_label, []).append(
            ModelRef(
                app_label=app_label,
                model_name=model._meta.model_name,
                verbose_name_plural=capfirst(model._meta.verbose_name_plural),
            )
        )

    for app_label in list(grouped.keys()):
        grouped[app_label].sort(key=lambda m: m.verbose_name_plural.lower())
    return dict(sorted(grouped.items(), key=lambda kv: kv[0].lower()))


def build_modelform(model: type[models.Model]):
    fields: list[str] = []
    for field in model._meta.get_fields():
        # Only concrete editable fields + m2m that are editable
        if not getattr(field, "editable", False):
            continue
        if getattr(field, "many_to_many", False) and getattr(field, "auto_created", False):
            continue
        if isinstance(field, models.Field) and _is_auto_or_uneditable_field(field):
            continue
        if hasattr(field, "name"):
            fields.append(field.name)

    if not fields:
        # Fallback: allow no fields (rare), but Django modelform_factory
        # requires explicit fields/exclude. We use exclude=[] to allow defaults.
        return modelform_factory(model, exclude=[])

    return modelform_factory(model, fields=fields)


def build_search_q(model: type[models.Model], q: str) -> Q:
    q_obj = Q()
    if not q:
        return q_obj

    for field in model._meta.get_fields():
        if not isinstance(field, models.Field):
            continue
        if isinstance(field, (models.CharField, models.TextField, models.EmailField, models.SlugField)):
            q_obj |= Q(**{f"{field.name}__icontains": q})
    return q_obj


def safe_pk_field(model: type[models.Model]) -> models.Field:
    return model._meta.pk


class StaffRequiredMixin(LoginRequiredMixin):
    login_url = reverse_lazy("back_office:login")

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Let LoginRequiredMixin handle unauthenticated users (redirect to login).
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        # Authenticated but not staff => forbidden.
        if not request.user.is_staff:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated and self.request.user.is_staff:
            ctx.setdefault("apps_models", list_registered_models_for_user(self.request))
        return ctx


class StaffLoginView(LoginView):
    template_name = "back_office/login.html"
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self) -> str:
        return reverse("back_office:dashboard")


def staff_logout(request: HttpRequest) -> HttpResponse:
    if request.method not in {"POST", "GET"}:
        raise Http404
    django_logout(request)
    return redirect("back_office:login")


class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = "back_office/dashboard.html"


class ModelContextMixin(StaffRequiredMixin):
    model: type[models.Model]

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.model = get_model_or_404(kwargs["app_label"], kwargs["model_name"])

    def require_perm(self, action: str) -> None:
        if not self.request.user.has_perm(perm_codename(action, self.model)):
            raise PermissionDenied

    def base_context(self) -> dict[str, Any]:
        model = self.model
        return {
            "apps_models": list_registered_models_for_user(self.request),
            "model_meta": model._meta,
            "model_ref": ModelRef(
                app_label=model._meta.app_label,
                model_name=model._meta.model_name,
                verbose_name_plural=capfirst(model._meta.verbose_name_plural),
            ),
            "perm": {
                "view": self.request.user.has_perm(perm_codename("view", model)),
                "add": self.request.user.has_perm(perm_codename("add", model)),
                "change": self.request.user.has_perm(perm_codename("change", model)),
                "delete": self.request.user.has_perm(perm_codename("delete", model)),
            },
        }


class ModelListView(ModelContextMixin, TemplateView):
    template_name = "back_office/model_list.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        self.require_perm("view")

        ctx = super().get_context_data(**kwargs)
        model = self.model
        qs = model._default_manager.all()

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(build_search_q(model, q))

        order = (self.request.GET.get("o") or "").strip()
        if order:
            try:
                model._meta.get_field(order)
                qs = qs.order_by(order)
            except FieldDoesNotExist:
                pass

        paginator = Paginator(qs, 25)
        page = paginator.get_page(self.request.GET.get("page"))

        # Choose display fields (first few concrete fields)
        display_fields: list[models.Field] = []
        hidden_field_names = {"id", "f"}
        for f in model._meta.fields:
            if f.name in hidden_field_names:
                continue
            if f is model._meta.pk:
                # Avoid showing PK (often UUID) in list view; actions cover edit/delete.
                continue
            if _is_auto_or_uneditable_field(f) and f is not model._meta.pk:
                continue
            display_fields.append(f)
            if len(display_fields) >= 6:
                break
        # If everything got filtered out, show at least one non-PK field if possible.
        if not display_fields:
            for f in model._meta.fields:
                if f is model._meta.pk or f.name in hidden_field_names:
                    continue
                display_fields.append(f)
                break

        ctx.update(self.base_context())
        ctx.update(
            {
                "q": q,
                "order": order,
                "page_obj": page,
                "paginator": paginator,
                "object_list": page.object_list,
                "display_fields": display_fields,
                "pk_field": safe_pk_field(model),
            }
        )
        return ctx


class ModelCreateView(ModelContextMixin, FormView):
    template_name = "back_office/model_form.html"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.require_perm("add")
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return build_modelform(self.model)

    def form_valid(self, form):
        obj = form.save()
        messages.success(self.request, f"Created {obj}.")
        return redirect(
            "back_office:model_list",
            app_label=self.model._meta.app_label,
            model_name=self.model._meta.model_name,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.base_context())
        ctx.update({"mode": "create"})
        return ctx


class ModelUpdateView(ModelContextMixin, FormView):
    template_name = "back_office/model_form.html"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.require_perm("change")
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return build_modelform(self.model)

    def get_object(self):
        pk = self.kwargs["pk"]
        return self.model._default_manager.get(pk=pk)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["instance"] = self.get_object()
        return kw

    def form_valid(self, form):
        obj = form.save()
        messages.success(self.request, f"Updated {obj}.")
        return redirect(
            "back_office:model_list",
            app_label=self.model._meta.app_label,
            model_name=self.model._meta.model_name,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.base_context())
        ctx.update({"mode": "edit", "object": self.get_object()})
        return ctx


class BackOfficeSettingsView(StaffRequiredMixin, TemplateView):
    """Admin settings hub for media storage and social provider credentials."""

    template_name = "back_office/settings.html"
    valid_tabs = {"media", "providers", "auth", "more"}

    def get_media_form(self, data=None) -> MediaUploadSettingsForm:
        return MediaUploadSettingsForm(data=data, instance=MediaUploadSettings.load())

    def get_provider_form(self, data=None) -> SocialProviderSettingsForm:
        return SocialProviderSettingsForm(data=data, instance=SocialProviderSettings.load())

    def get_mail_form(self, data=None) -> AppMailSettingsForm:
        return AppMailSettingsForm(data=data, instance=AppMailSettings.load(), prefix="mail")

    def get_auth_template_forms(self, data=None) -> dict[str, AuthEmailTemplateForm]:
        forms: dict[str, AuthEmailTemplateForm] = {}
        for key in AUTH_EMAIL_TEMPLATE_DEFAULTS:
            forms[key] = AuthEmailTemplateForm(
                data=data,
                instance=AuthEmailTemplate.load(key),
                prefix=key,
            )
        return forms

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        section = request.POST.get("settings_section", "media")

        if section == "providers":
            media_form = self.get_media_form()
            provider_form = self.get_provider_form(data=request.POST)
            mail_form = self.get_mail_form()
            auth_template_forms = self.get_auth_template_forms()
            if provider_form.is_valid():
                provider_form.save()
                messages.success(request, "Provider settings saved.")
                return redirect(f"{reverse('back_office:settings')}?tab=providers#tab-providers")
            return self.render_to_response(self.get_context_data(
                form=media_form,
                provider_form=provider_form,
                mail_form=mail_form,
                auth_template_forms=auth_template_forms,
                active_settings_tab="providers",
            ))

        if section == "auth":
            media_form = self.get_media_form()
            provider_form = self.get_provider_form()
            mail_form = self.get_mail_form(data=request.POST)
            auth_template_forms = self.get_auth_template_forms(data=request.POST)
            if mail_form.is_valid() and all(form.is_valid() for form in auth_template_forms.values()):
                mail_form.save()
                for form in auth_template_forms.values():
                    form.save()
                messages.success(request, "Auth mail settings saved.")
                return redirect(f"{reverse('back_office:settings')}?tab=auth#tab-auth")
            return self.render_to_response(self.get_context_data(
                form=media_form,
                provider_form=provider_form,
                mail_form=mail_form,
                auth_template_forms=auth_template_forms,
                active_settings_tab="auth",
            ))

        media_form = self.get_media_form(data=request.POST)
        provider_form = self.get_provider_form()
        mail_form = self.get_mail_form()
        auth_template_forms = self.get_auth_template_forms()
        if media_form.is_valid():
            media_form.save()
            messages.success(request, "Media settings saved.")
            return redirect(f"{reverse('back_office:settings')}?tab=media#tab-media")
        return self.render_to_response(self.get_context_data(
            form=media_form,
            provider_form=provider_form,
            mail_form=mail_form,
            auth_template_forms=auth_template_forms,
            active_settings_tab="media",
        ))

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("form", self.get_media_form())
        ctx.setdefault("provider_form", self.get_provider_form())
        ctx.setdefault("mail_form", self.get_mail_form())
        ctx.setdefault("auth_template_forms", self.get_auth_template_forms())
        ctx.setdefault(
            "auth_template_help",
            {
                "welcome": AUTH_EMAIL_TEMPLATE_DEFAULTS["welcome"]["description"],
                "password_reset": AUTH_EMAIL_TEMPLATE_DEFAULTS["password_reset"]["description"],
            },
        )
        requested_tab = (self.request.GET.get("tab") or "").strip().lower()
        ctx.setdefault(
            "active_settings_tab",
            requested_tab if requested_tab in self.valid_tabs else "media",
        )
        return ctx


class ModelDeleteView(ModelContextMixin, View):
    template_name = "back_office/model_confirm_delete.html"

    def get_object(self):
        pk = self.kwargs["pk"]
        return self.model._default_manager.get(pk=pk)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.require_perm("delete")
        ctx = self.base_context()
        ctx["object"] = self.get_object()
        return render(request, self.template_name, ctx)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.require_perm("delete")
        obj = self.get_object()
        obj_display = str(obj)
        obj.delete()
        messages.success(request, f"Deleted {obj_display}.")
        return redirect(
            "back_office:model_list",
            app_label=self.model._meta.app_label,
            model_name=self.model._meta.model_name,
        )

