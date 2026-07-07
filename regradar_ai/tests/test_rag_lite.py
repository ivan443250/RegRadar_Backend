"""RAG-lite retrieval, endpoint grounding, audience and fallback tests."""

import pytest

from app.ai.gateway.base import LLMRawResponse
from app.ai.gateway.polza_provider import PolzaAIProvider
from app.ai.rag_context_store import clear_document_contexts
from app.ai.rag_retrieval import (
    MIN_RELEVANCE_SCORE,
    is_document_level_question,
    normalize_query,
    retrieve_top_fragments,
    score_fragment,
    tokenize_ru,
)
from app.ai.rag_service import sanitize_rag_answer
from app.ai.schemas import RagFragmentInput


@pytest.fixture(autouse=True)
def clean_rag_store():
    clear_document_contexts()
    yield
    clear_document_contexts()


FRAGMENT = RagFragmentInput(
    text="Банк обязан выполнить требования в срок до 1 июля.",
    document_id="doc-1",
    version_id="v1",
    chunk_id="chunk-1",
    role="document_chunk",
)


def test_retrieval_normalization_and_tokens():
    assert normalize_query("Ёлка, БАНК!") == "елка банк"
    assert tokenize_ru("Какой срок установлен банку?") == {
        "какой",
        "срок",
        "установлен",
        "банку",
    }


def test_retrieval_finds_relevant_fragment():
    results = retrieve_top_fragments(
        "Какой срок должен соблюдать банк?",
        [FRAGMENT],
    )
    assert results
    assert results[0].chunk_id == "chunk-1"
    assert results[0].score > 0
    assert score_fragment("Какой срок для банка?", FRAGMENT.text) > 0


def test_retrieval_returns_empty_for_irrelevant_question():
    assert retrieve_top_fragments("Какая погода на Марсе?", [FRAGMENT]) == []


def test_retrieval_discards_scores_below_minimum():
    assert MIN_RELEVANCE_SCORE > 0
    assert score_fragment("Какая погода на Марсе?", FRAGMENT.text) < MIN_RELEVANCE_SCORE


@pytest.mark.parametrize(
    "question",
    [
        "Почему этот документ получил такой impact?",
        "Каких клиентов он затрагивает?",
        "Что банк должен проверить?",
        "Сформируй объяснение клиенту простым языком.",
        "Покажи источники, на которых основан вывод.",
    ],
)
def test_document_level_questions_retrieve_grounding_context(question):
    assert is_document_level_question(question) is True
    results = retrieve_top_fragments(question, [FRAGMENT])
    assert results
    assert results[0].chunk_id == FRAGMENT.chunk_id


def test_rag_endpoint_returns_no_data_without_sources(client):
    response = client.post(
        "/api/rag/ask",
        json={"question": "Какой срок?", "document_id": "unknown"},
    )
    data = response.json()
    assert response.status_code == 200
    assert data["no_data"] is True
    assert data["answer"] == "Нет данных в базе по этому вопросу."
    assert data["source_fragments"] == []
    assert data["metadata"]["provider"] == "none"


def test_rag_endpoint_answers_document_level_impact_question(client):
    response = client.post(
        "/api/rag/ask",
        json={
            "question": "Почему этот документ получил такой impact?",
            "source_fragments": [FRAGMENT.model_dump()],
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["no_data"] is False
    assert data["source_fragments"][0]["chunk_id"] == FRAGMENT.chunk_id


def test_rag_answer_hides_raw_source_identifiers():
    answer = sanitize_rag_answer(
        "Вывод по document_id=doc-1, version_id=v1 и chunk_1 подтверждён chunk-1.",
        [FRAGMENT],
    )
    assert "document_id" not in answer
    assert "version_id" not in answer
    assert "chunk_1" not in answer
    assert "chunk-1" not in answer
    assert "doc-1" not in answer


@pytest.mark.parametrize(
    ("audience", "notice"),
    [
        (
            "bank_employee",
            "требует проверки профильным специалистом",
        ),
        (
            "client",
            "не является юридической консультацией",
        ),
    ],
)
def test_rag_endpoint_answers_with_sources_and_audience_notice(
    client,
    audience,
    notice,
):
    response = client.post(
        "/api/rag/ask",
        json={
            "question": "Какой срок установлен для банка?",
            "audience": audience,
            "source_fragments": [FRAGMENT.model_dump()],
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["no_data"] is False
    assert data["answer"]
    assert notice in data["safety_notice"]
    assert data["source_fragments"][0]["text"] == FRAGMENT.text
    assert data["source_fragments"][0]["document_id"] == "doc-1"
    assert data["source_fragments"][0]["chunk_id"] == "chunk-1"


def test_rag_invalid_llm_schema_uses_extractive_fallback(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza_with_fallback")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    monkeypatch.setenv("POLZA_MAX_RETRIES", "0")

    def invalid_schema(self, request):
        return LLMRawResponse(
            raw_text='{"unrelated": true}',
            model=request.model or "model",
            provider="polza",
        )

    monkeypatch.setattr(PolzaAIProvider, "complete", invalid_schema)
    response = client.post(
        "/api/rag/ask",
        json={
            "question": "Какой срок установлен для банка?",
            "source_fragments": [FRAGMENT.model_dump()],
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["no_data"] is False
    assert data["answer"].startswith(
        "На основании найденных фрагментов можно сделать предварительный вывод"
    )
    assert data["metadata"]["fallback_used"] is True
    assert data["metadata"]["fallback_reason"]
    assert data["source_fragments"]


def test_rag_polza_answer_is_sanitized_but_sources_keep_ids(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza_with_fallback")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")

    def answer_with_raw_ids(self, request):
        return LLMRawResponse(
            raw_text=(
                '{"answer":"Вывод подтверждают document_id=doc-1, '
                'version_id=v1 и chunk_1.","no_data":false,'
                '"used_fragment_ids":["chunk-1"],"safety_notice":""}'
            ),
            model=request.model or "model",
            provider="polza",
        )

    monkeypatch.setattr(PolzaAIProvider, "complete", answer_with_raw_ids)
    response = client.post(
        "/api/rag/ask",
        json={
            "question": "Что банк должен проверить?",
            "source_fragments": [FRAGMENT.model_dump()],
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["no_data"] is False
    assert "document_id" not in data["answer"]
    assert "version_id" not in data["answer"]
    assert "chunk_1" not in data["answer"]
    assert data["source_fragments"][0]["document_id"] == "doc-1"
    assert data["source_fragments"][0]["version_id"] == "v1"
    assert data["source_fragments"][0]["chunk_id"] == "chunk-1"


def test_upload_card_context_can_be_queried_without_request_fragments(client):
    upload = client.post(
        "/api/documents/upload-create-card",
        files={
            "file": (
                "bank-rule.txt",
                FRAGMENT.text.encode("utf-8"),
                "text/plain",
            )
        },
        data={"document_id": "cached-doc", "version_id": "v1"},
    )
    assert upload.status_code == 200

    response = client.post(
        "/api/rag/ask",
        json={
            "question": "Какой срок установлен для банка?",
            "document_id": "cached-doc",
            "version_id": "v1",
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["no_data"] is False
    assert data["source_fragments"]
    assert all(item["document_id"] == "cached-doc" for item in data["source_fragments"])
