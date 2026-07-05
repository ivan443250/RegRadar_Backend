"""Lightweight Russian-language guard for LLM user-visible fields."""

import re

from .schemas import DocumentAnalysis


_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_LATIN_TOKEN = re.compile(r"\b[A-Za-z][A-Za-z0-9._/-]*\b")
_ALLOWED_ABBREVIATIONS = {"API", "PDF", "JSON", "URL", "ID"}
_ALLOWED_TECHNICAL_TERMS = {"no-match"}

_VISIBLE_FIELDS: tuple[str, ...] = (
    "title",
    "short_summary",
    "long_summary",
    "status",
    "topics",
    "affected_processes",
    "affected_industries",
    "obligations",
    "restrictions",
    "penalties_or_consequences",
    "key_dates",
)


def _remove_allowed_latin_tokens(text: str) -> str:
    without_urls = _URL_PATTERN.sub(" ", text)

    def replace_token(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.casefold() in _ALLOWED_TECHNICAL_TERMS:
            return " "
        if token.upper() in _ALLOWED_ABBREVIATIONS:
            return " "
        if len(token) <= 4 and token.isupper():
            return " "
        return token

    return _LATIN_TOKEN.sub(replace_token, without_urls)


def is_mostly_russian_text(text: str) -> bool:
    """Return False only when meaningful Latin text dominates Cyrillic text."""
    cleaned = _remove_allowed_latin_tokens(text)
    cyrillic_count = len(re.findall(r"[А-Яа-яЁё]", cleaned))
    latin_count = len(re.findall(r"[A-Za-z]", cleaned))
    if latin_count == 0:
        return True
    return cyrillic_count >= latin_count * 2


def validate_document_analysis_language(
    analysis: DocumentAnalysis,
) -> list[str]:
    """Return stable warnings for non-Russian user-visible fields."""
    warnings: list[str] = []
    for field_name in _VISIBLE_FIELDS:
        value = getattr(analysis, field_name)
        values = value if isinstance(value, list) else [value]
        non_empty = [str(item) for item in values if item]
        if non_empty and any(
            not is_mostly_russian_text(item) for item in non_empty
        ):
            warnings.append(f"LLM returned non-Russian {field_name}")
    return warnings
