"""Safety gate applied immediately before mock notification delivery."""

from __future__ import annotations

from typing import Any

from .schemas import NotificationDraft


STANDARD_NOTIFICATION_DISCLAIMER = (
    "Это информационное уведомление и не является юридической консультацией."
)
PROHIBITED_PHRASES = (
    "вы обязаны",
    "гарантируем",
    "точно применимо",
    "официальный документ",
)


def ensure_notification_disclaimer(
    notification: NotificationDraft,
) -> NotificationDraft:
    if notification.disclaimer.strip():
        return notification
    return notification.model_copy(
        update={"disclaimer": STANDARD_NOTIFICATION_DISCLAIMER}
    )


def _value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def validate_notification_can_be_sent(
    notification: NotificationDraft,
    client_relevance: list[Any] | None = None,
    document_analysis_or_event_card: Any | None = None,
) -> list[str]:
    errors: list[str] = []
    for field_name in ("title", "short_message", "full_message"):
        if not str(getattr(notification, field_name, "")).strip():
            errors.append(f"notification {field_name} is required")
    if not notification.disclaimer.strip():
        errors.append("notification disclaimer is required")

    combined = " ".join(
        (
            notification.title,
            notification.short_message,
            notification.full_message,
        )
    ).casefold()
    combined = combined.replace(
        "не является юридической консультацией",
        "",
    )
    for phrase in PROHIBITED_PHRASES:
        if phrase in combined:
            errors.append(f"prohibited categorical phrase: {phrase}")
    if "юридическая консультация" in combined:
        errors.append("notification must not present itself as legal advice")

    context = document_analysis_or_event_card
    document_analysis = _value(context, "document_analysis", {})
    domain = _value(document_analysis, "domain") or _value(context, "domain")
    if domain == "neutral_no_match":
        errors.append("neutral_no_match notifications are blocked")

    if client_relevance is not None:
        relevant_ids = {
            str(_value(item, "client_id", ""))
            for item in client_relevance
            if _value(item, "client_id")
        }
        if notification.client_id not in relevant_ids:
            errors.append("client is not relevant to this document")
    return errors

