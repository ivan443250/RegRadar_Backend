"""Append-only, privacy-safe JSONL audit trail for AI/LLM calls."""

from __future__ import annotations

import json
import logging
import re
from threading import RLock
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from ..storage.paths import log_dir


logger = logging.getLogger(__name__)
LOG_PATH = log_dir() / "llm_calls.jsonl"
_LOG_LOCK = RLock()

Operation = Literal[
    "document_analysis",
    "rag_answer",
    "language_retry",
    "fallback",
    "mock",
    "gateway_test",
]
CallStatus = Literal[
    "success",
    "fallback",
    "error",
    "validation_error",
    "timeout",
    "skipped",
]

_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "token",
    "secret",
    "password",
    "prompt",
    "document_text",
    "source_fragments",
    "rag_fragments",
    "chunks",
)

_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?\S+"),
    re.compile(r"(?i)(bearer\s+)\S+"),
    re.compile(
        r"(?i)((?:polza|polzaai)_api_key|api_key|client_secret|password)"
        r"(\s*[:=]\s*)\S+"
    ),
    re.compile(r"(?i)\b(?:polza_api_key|polzaai_api_key|api_key|client_secret)\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)


def sanitize_log_text(
    value: Any,
    sensitive_values: tuple[str, ...] = (),
) -> str | None:
    if value is None:
        return None
    cleaned = str(value)
    for sensitive_value in sensitive_values:
        if sensitive_value and len(sensitive_value) >= 8:
            cleaned = cleaned.replace(sensitive_value, "[REDACTED]")
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub(
            lambda match: (
                f"{''.join(group or '' for group in match.groups())}[REDACTED]"
                if match.lastindex
                else "[REDACTED]"
            ),
            cleaned,
        )
    return cleaned[:500]


def _safe_metadata(value: Any, *, key: str = "") -> Any:
    normalized_key = key.casefold()
    if any(part in normalized_key for part in _SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return sanitize_log_text(value)
    if isinstance(value, dict):
        return {
            str(child_key): _safe_metadata(child_value, key=str(child_key))
            for child_key, child_value in value.items()
            if not any(
                part in str(child_key).casefold()
                for part in _SENSITIVE_KEY_PARTS
            )
        }
    if isinstance(value, (list, tuple, set)):
        return [_safe_metadata(item, key=key) for item in list(value)[:50]]
    return str(value)[:500]


class LLMCallLogRecord(BaseModel):
    call_id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str | None = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    endpoint: str | None = None
    operation: Operation
    provider: str
    runtime: str
    model: str | None = None
    selected_model: str | None = None
    prompt_version: str | None = None
    status: CallStatus
    latency_ms: int | None = Field(default=None, ge=0)
    input_chars: int | None = Field(default=None, ge=0)
    output_chars: int | None = Field(default=None, ge=0)
    input_tokens_estimate: int | None = Field(default=None, ge=0)
    output_tokens_estimate: int | None = Field(default=None, ge=0)
    fallback_used: bool = False
    fallback_reason: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("error_message", "fallback_reason", mode="before")
    @classmethod
    def truncate_error_text(cls, value: Any) -> Any:
        return sanitize_log_text(value)

    @field_validator("warnings", mode="before")
    @classmethod
    def truncate_warnings(cls, value: Any) -> list[str]:
        return [sanitize_log_text(item) or "" for item in (value or [])]

    @field_validator("metadata", mode="before")
    @classmethod
    def sanitize_metadata(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return _safe_metadata(value)


def log_llm_call(record: LLMCallLogRecord) -> None:
    """Append a record; audit failures never interrupt the product pipeline."""
    try:
        with _LOG_LOCK:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        record.model_dump(mode="json"),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
    except OSError as error:
        logger.warning("Could not append LLM audit log: %s", error)


def read_recent_llm_calls(limit: int = 50) -> list[LLMCallLogRecord]:
    safe_limit = min(max(int(limit), 0), 200)
    if safe_limit == 0 or not LOG_PATH.exists():
        return []
    try:
        with _LOG_LOCK:
            lines = LOG_PATH.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        logger.warning("Could not read LLM audit log: %s", error)
        return []
    records: list[LLMCallLogRecord] = []
    for line in lines[-safe_limit:]:
        try:
            records.append(LLMCallLogRecord.model_validate_json(line))
        except (ValueError, TypeError) as error:
            logger.warning("Skipping invalid LLM audit log line: %s", error)
    return records


def clear_llm_call_logs_for_tests() -> None:
    try:
        with _LOG_LOCK:
            LOG_PATH.unlink(missing_ok=True)
    except OSError as error:
        logger.warning("Could not clear LLM audit log: %s", error)


def estimate_tokens(chars: int | None) -> int | None:
    return chars // 4 if chars is not None else None
