"""RegulatoryEventCard persistence-lite repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from .jsonl_repository import append_jsonl, find_latest_by_fields, read_jsonl_reverse
from .paths import storage_dir


STORAGE_DIR = storage_dir()
EVENTS_PATH = STORAGE_DIR / "events.jsonl"


class EventCardRecord(BaseModel):
    event_id: str
    document_id: str
    version_id: str = "v1"
    title: str
    domain: str | None = None
    topics: list[str] = Field(default_factory=list)
    impact_score: int | None = None
    impact_level: str | None = None
    review_state: str | None = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    event_card: dict[str, Any]


def save_event_card(
    event_card: BaseModel | dict[str, Any],
    document_id: str | None = None,
    version_id: str = "v1",
) -> bool:
    payload = (
        event_card.model_dump(mode="json")
        if isinstance(event_card, BaseModel)
        else dict(event_card)
    )
    analysis_metadata = payload.get("analysis_metadata") or {}
    evidence = payload.get("evidence_fragments") or []
    first_evidence = evidence[0] if evidence and isinstance(evidence[0], dict) else {}
    effective_document_id = (
        document_id
        or analysis_metadata.get("context_document_id")
        or first_evidence.get("document_id")
        or "unknown"
    )
    effective_version_id = (
        version_id
        or analysis_metadata.get("context_version_id")
        or first_evidence.get("version_id")
        or "v1"
    )
    document_analysis = payload.get("document_analysis") or {}
    record = EventCardRecord(
        event_id=str(payload.get("event_id")),
        document_id=str(effective_document_id),
        version_id=str(effective_version_id),
        title=str(payload.get("title", "")),
        domain=document_analysis.get("domain"),
        topics=list(payload.get("topics") or []),
        impact_score=payload.get("impact_score"),
        impact_level=payload.get("impact_level"),
        review_state=payload.get("review_state"),
        metadata={
            "request_id": analysis_metadata.get("request_id"),
            "llm_call_ids": analysis_metadata.get("llm_call_ids") or [],
        },
        event_card=payload,
    )
    return append_jsonl(EVENTS_PATH, record.model_dump(mode="json"))


def get_event_card(event_id: str) -> dict[str, Any] | None:
    value = find_latest_by_fields(EVENTS_PATH, {"event_id": event_id})
    return value.get("event_card") if value else None


def get_latest_event_by_document(
    document_id: str,
    version_id: str = "v1",
) -> dict[str, Any] | None:
    return find_latest_by_fields(
        EVENTS_PATH,
        {"document_id": document_id, "version_id": version_id},
    )


def list_event_cards(limit: int = 50) -> list[dict[str, Any]]:
    return read_jsonl_reverse(EVENTS_PATH, limit=limit)
