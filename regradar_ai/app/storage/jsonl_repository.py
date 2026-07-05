"""Small append-only JSONL primitives shared by persistence-lite repositories."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import RLock
from typing import Any


logger = logging.getLogger(__name__)
_LOCK = RLock()


def append_jsonl(path: Path, record: dict[str, Any]) -> bool:
    try:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
        return True
    except (OSError, TypeError, ValueError) as error:
        logger.warning("Could not append JSONL record to %s: %s", path, error)
        return False


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with _LOCK:
            lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        logger.warning("Could not read JSONL repository %s: %s", path, error)
        return []
    if limit is not None:
        lines = lines[:max(limit, 0)]
    records: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
        except (json.JSONDecodeError, TypeError) as error:
            logger.warning("Skipping invalid JSONL line in %s: %s", path, error)
    return records


def read_jsonl_reverse(path: Path, limit: int = 50) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    records = read_jsonl(path)
    return list(reversed(records[-limit:]))


def _matches(record: dict[str, Any], filters: dict[str, Any]) -> bool:
    return all(record.get(key) == value for key, value in filters.items())


def find_latest_by_fields(
    path: Path,
    filters: dict[str, Any],
) -> dict[str, Any] | None:
    for record in read_jsonl_reverse(path, limit=2_000_000_000):
        if _matches(record, filters):
            return record
    return None


def find_many_by_fields(
    path: Path,
    filters: dict[str, Any],
    limit: int | None = None,
) -> list[dict[str, Any]]:
    matches = [record for record in read_jsonl(path) if _matches(record, filters)]
    return matches if limit is None else matches[:max(limit, 0)]


def clear_jsonl_for_tests(path: Path) -> None:
    try:
        with _LOCK:
            path.unlink(missing_ok=True)
    except OSError as error:
        logger.warning("Could not clear JSONL repository %s: %s", path, error)
