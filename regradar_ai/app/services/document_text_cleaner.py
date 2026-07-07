"""Small, deterministic cleanup helpers for extracted document text."""

import re


EVAL_METADATA_FIELDS: tuple[str, ...] = (
    "DOCUMENT_TITLE",
    "DOCUMENT_DATE",
    "DOCUMENT_TYPE_EXPECTED",
    "DOMAIN_EXPECTED",
    "SOURCE_FILE",
    "TOPICS_EXPECTED",
    "IMPACT_LEVEL_EXPECTED",
)

_EVAL_METADATA_LINE = re.compile(
    rf"^[ \t]*(?:{'|'.join(EVAL_METADATA_FIELDS)})[ \t]*:.*(?:\r?\n|$)",
    flags=re.IGNORECASE | re.MULTILINE,
)


def clean_eval_metadata(text: str) -> str:
    """Remove repository eval annotation lines from extracted source text.

    Only complete lines with known metadata prefixes are removed. Legal text
    containing ordinary words such as ``document`` or ``title`` is untouched.
    """
    return _EVAL_METADATA_LINE.sub("", text).strip()
