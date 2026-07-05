"""Mock notification delivery repository backed by JSONL."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .jsonl_repository import append_jsonl, find_latest_by_fields, read_jsonl_reverse
from .paths import storage_dir


STORAGE_DIR = storage_dir()
NOTIFICATIONS_PATH = STORAGE_DIR / "notifications.jsonl"

NotificationChannel = Literal["mock", "email_mock", "bank_app_mock", "webhook_mock"]
DeliveryStatus = Literal["draft", "sent_mock", "failed_mock", "skipped"]
_SENSITIVE_KEYS = {"api_key", "authorization", "secret", "token", "password", "env"}


def _safe_preview(value: Any, key: str = "") -> Any:
    if any(marker in key.casefold() for marker in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {
            str(child_key): _safe_preview(child, str(child_key))
            for child_key, child in value.items()
            if not any(marker in str(child_key).casefold() for marker in _SENSITIVE_KEYS)
        }
    if isinstance(value, (list, tuple)):
        return [_safe_preview(item, key) for item in list(value)[:50]]
    if isinstance(value, str):
        return value[:2000]
    return value


class NotificationDeliveryRecord(BaseModel):
    notification_id: str
    delivery_id: str
    event_id: str | None = None
    document_id: str
    version_id: str = "v1"
    client_id: str
    client_name: str | None = None
    notification_title: str
    channel: NotificationChannel = "mock"
    status: DeliveryStatus
    priority: str | None = None
    disclaimer: str
    source_link: str | None = None
    source_chunk_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    sent_at: str | None = None
    payload_preview: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload_preview", "metadata", mode="before")
    @classmethod
    def sanitize_payload(cls, value: Any) -> dict[str, Any]:
        return _safe_preview(value if isinstance(value, dict) else {})


def save_delivery(record: NotificationDeliveryRecord) -> bool:
    return append_jsonl(NOTIFICATIONS_PATH, record.model_dump(mode="json"))


def list_deliveries(limit: int = 50) -> list[dict[str, Any]]:
    return read_jsonl_reverse(NOTIFICATIONS_PATH, limit)


def list_deliveries_by_document(
    document_id: str,
    version_id: str = "v1",
    limit: int = 50,
) -> list[dict[str, Any]]:
    return [
        record
        for record in read_jsonl_reverse(NOTIFICATIONS_PATH, 2_000_000_000)
        if record.get("document_id") == document_id
        and record.get("version_id") == version_id
    ][:max(limit, 0)]


def list_deliveries_by_client(
    client_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    return [
        record
        for record in read_jsonl_reverse(NOTIFICATIONS_PATH, 2_000_000_000)
        if record.get("client_id") == client_id
    ][:max(limit, 0)]


def get_delivery(delivery_id: str) -> dict[str, Any] | None:
    return find_latest_by_fields(NOTIFICATIONS_PATH, {"delivery_id": delivery_id})
