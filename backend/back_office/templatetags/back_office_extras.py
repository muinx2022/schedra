from django import template

register = template.Library()


@register.filter
def attr(obj, name: str):
    try:
        return getattr(obj, name)
    except Exception:
        return ""


@register.filter
def icon_for_app(app_label: str) -> str:
    key = (app_label or "").lower()
    mapping = {
        "accounts": "bi-people-fill",
        "ideas": "bi-lightbulb-fill",
        "media_library": "bi-images",
        "social": "bi-share-fill",
        "publishing": "bi-file-earmark-text-fill",
        "common": "bi-gear-fill",
    }
    return mapping.get(key, "bi-folder2-open")


@register.filter
def icon_for_model(model_name: str) -> str:
    key = (model_name or "").lower()
    if "user" in key:
        return "bi-person-fill"
    if "idea" in key:
        return "bi-lightbulb"
    if "media" in key or "asset" in key or "image" in key:
        return "bi-image"
    if "post" in key or "publish" in key:
        return "bi-file-text"
    if "account" in key:
        return "bi-person-badge"
    if "connect" in key or "link" in key:
        return "bi-link-45deg"
    if "setting" in key or "config" in key:
        return "bi-sliders"
    return "bi-table"

