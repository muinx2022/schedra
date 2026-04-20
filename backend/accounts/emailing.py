import logging
from email.utils import formataddr
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template
from django.template.defaultfilters import striptags
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from back_office.models import AppMailSettings, AuthEmailTemplate

logger = logging.getLogger(__name__)


def _render_string(template_source: str, context: dict[str, object]) -> str:
    return Template(template_source).render(Context(context)).strip()


def _frontend_base_url(request=None) -> str:
    settings_obj = AppMailSettings.load()
    if settings_obj.frontend_base_url:
        return settings_obj.frontend_base_url.rstrip("/")

    configured = getattr(settings, "APP_PUBLIC_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")

    if request:
        origin = (request.headers.get("origin") or "").strip()
        if origin:
            return origin.rstrip("/")
        return request.build_absolute_uri("/").rstrip("/")

    return "http://127.0.0.1:3000"


def _mail_sender() -> tuple[str, list[str]]:
    mail_settings = AppMailSettings.load()
    configured_from = mail_settings.from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "")
    from_name = mail_settings.from_name or mail_settings.site_name or getattr(settings, "APP_SITE_NAME", "Social Man")
    reply_to_email = mail_settings.reply_to_email.strip()

    if configured_from:
        from_email = formataddr((from_name, configured_from))
    else:
        from_email = ""

    reply_to = [reply_to_email] if reply_to_email else []
    return from_email, reply_to


def send_auth_email(template_key: str, to_email: str, context: dict[str, object]) -> bool:
    template = AuthEmailTemplate.load(template_key)
    subject = _render_string(template.subject, context)
    text_body = _render_string(template.text_body, context) if template.text_body else ""
    html_body = _render_string(template.html_body, context) if template.html_body else ""

    if not text_body and html_body:
        text_body = striptags(html_body)
    if not subject or not (text_body or html_body):
        logger.warning("Auth email template %s is incomplete; skipping send.", template_key)
        return False

    from_email, reply_to = _mail_sender()
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email or None,
        to=[to_email],
        reply_to=reply_to,
    )
    if html_body:
        message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)
    return True


def send_welcome_email(user, request=None) -> bool:
    mail_settings = AppMailSettings.load()
    if not mail_settings.send_welcome_email or not user.email:
        return False

    workspace_name = getattr(getattr(user, "workspace", None), "name", "")
    base_url = _frontend_base_url(request)
    context = {
        "site_name": mail_settings.site_name or getattr(settings, "APP_SITE_NAME", "Social Man"),
        "first_name": user.first_name,
        "full_name": user.get_full_name().strip() or user.username,
        "email": user.email,
        "workspace_name": workspace_name,
        "login_url": f"{base_url}/login",
    }
    return send_auth_email("welcome", user.email, context)


def send_password_reset_email(user, request=None, expires_in_minutes: int = 60) -> bool:
    mail_settings = AppMailSettings.load()
    if not mail_settings.send_password_reset_email or not user.email:
        return False

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    base_url = _frontend_base_url(request)
    reset_path = (mail_settings.password_reset_path or "/reset-password").strip() or "/reset-password"
    reset_url = urljoin(f"{base_url}/", reset_path.lstrip("/"))
    joiner = "&" if "?" in reset_url else "?"
    reset_url = f"{reset_url}{joiner}uid={uid}&token={token}"

    context = {
        "site_name": mail_settings.site_name or getattr(settings, "APP_SITE_NAME", "Social Man"),
        "first_name": user.first_name,
        "full_name": user.get_full_name().strip() or user.username,
        "email": user.email,
        "reset_url": reset_url,
        "expires_in_minutes": expires_in_minutes,
    }
    return send_auth_email("password_reset", user.email, context)
