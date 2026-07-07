"""Deterministic keyword retrieval for the RAG-lite MVP."""

import re

from .schemas import RagFragmentInput, RagSourceFragment


IMPORTANT_TERMS = (
    "штраф",
    "срок",
    "обязанность",
    "клиент",
    "банк",
    "персональные данные",
    "платеж",
    "отчетность",
    "валютный контроль",
    "115-фз",
    "ценные бумаги",
    "акциз",
    "маркировка",
    "безопасность",
)

MIN_RELEVANCE_SCORE = 0.5

# These questions refer to the document as a whole rather than repeat its legal
# vocabulary. They still need source fragments for a grounded answer.
DOCUMENT_LEVEL_INTENT_MARKERS = (
    "impact",
    "влияни",
    "затрагива",
    "клиент",
    "банк должен",
    "банк обязан",
    "что банк",
    "провер",
    "объяснен",
    "объясни",
    "простым языком",
    "источник",
    "основан вывод",
    "почему документ",
    "этот документ",
)


def normalize_query(text: str) -> str:
    normalized = text.casefold().replace("ё", "е")
    normalized = re.sub(r"[^0-9a-zа-я-]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def tokenize_ru(text: str) -> set[str]:
    return {
        token
        for token in normalize_query(text).split()
        if len(token) >= 3
    }


def is_document_level_question(question: str) -> bool:
    normalized_question = normalize_query(question)
    return any(
        marker in normalized_question
        for marker in DOCUMENT_LEVEL_INTENT_MARKERS
    )


def score_fragment(question: str, fragment_text: str) -> float:
    question_tokens = tokenize_ru(question)
    fragment_tokens = tokenize_ru(fragment_text)
    score = float(len(question_tokens & fragment_tokens))
    normalized_question = normalize_query(question)
    normalized_fragment = normalize_query(fragment_text)
    for term in IMPORTANT_TERMS:
        normalized_term = normalize_query(term)
        if normalized_term in normalized_question and normalized_term in normalized_fragment:
            score += 2.0
    # A small score makes the document context available to the LLM for
    # document-level questions. It does not affect unrelated factual queries.
    if is_document_level_question(question):
        score += 1.0
    return score


def retrieve_top_fragments(
    question: str,
    fragments: list[RagFragmentInput],
    top_k: int = 5,
) -> list[RagSourceFragment]:
    scored: list[tuple[float, int, RagFragmentInput]] = []
    for index, fragment in enumerate(fragments):
        score = score_fragment(question, fragment.text)
        if score >= MIN_RELEVANCE_SCORE:
            scored.append((score, index, fragment))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        RagSourceFragment(
            text=fragment.text,
            document_id=fragment.document_id,
            version_id=fragment.version_id,
            chunk_id=fragment.chunk_id,
            score=score,
            role=fragment.role,
        )
        for score, _, fragment in scored[:top_k]
    ]
