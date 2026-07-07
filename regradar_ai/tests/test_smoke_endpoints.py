"""Smoke-тесты для всех endpoint'ов FastAPI."""


import logging

import pytest
from app.ai.mock_provider import analyze_document as analyze_document_legacy
from app.ai.gateway.errors import LLMProviderUnavailableError
from app.ai.schemas import DocumentAnalysis
from app.ai.service import full_ai_analysis


# --- GET /health ---


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "regradar-ai"


# --- POST /api/analyze ---


SAMPLE_TEXT = (
    "Проект предусматривает новые требования к обработке персональных данных "
    "клиентов. Организации должны обеспечить хранение согласий пользователей "
    "и соблюдать положения 152-ФЗ. За нарушение требований может наступать "
    "ответственность."
)


def test_analyze_returns_200(client):
    response = client.post("/api/analyze", json={"text": SAMPLE_TEXT})
    assert response.status_code == 200


def test_analyze_contains_event(client):
    data = client.post("/api/analyze", json={"text": SAMPLE_TEXT}).json()
    assert "event" in data
    event = data["event"]
    assert "title" in event
    assert "summary" in event
    assert "category" in event
    assert "impact" in event
    assert "impact_reason" in event


def test_analyze_contains_affected_clients(client):
    data = client.post("/api/analyze", json={"text": SAMPLE_TEXT}).json()
    assert "affected_clients" in data
    assert isinstance(data["affected_clients"], list)


def test_analyze_contains_notifications(client):
    data = client.post("/api/analyze", json={"text": SAMPLE_TEXT}).json()
    assert "notifications" in data
    assert isinstance(data["notifications"], list)


# --- POST /api/ai/full-analysis ---


def test_full_analysis_returns_200(client):
    response = client.post("/api/ai/full-analysis", json={"text": SAMPLE_TEXT})
    assert response.status_code == 200


def test_full_analysis_contains_all_blocks(client):
    data = client.post("/api/ai/full-analysis", json={"text": SAMPLE_TEXT}).json()
    assert "document_analysis" in data
    assert "impact_assessment" in data
    assert "client_relevance" in data
    assert "notification_drafts" in data
    assert "analysis_metadata" in data
    assert isinstance(data["client_relevance"], list)
    assert isinstance(data["notification_drafts"], list)
    assert data["analysis_metadata"]["fallback_used"] is False


def test_full_analysis_document_analysis_valid(client):
    data = client.post("/api/ai/full-analysis", json={"text": SAMPLE_TEXT}).json()
    doc = data["document_analysis"]
    assert doc["title"]
    assert doc["short_summary"]
    assert isinstance(doc["topics"], list)
    assert isinstance(doc["source_fragments"], list)
    assert 0.0 <= doc["confidence"] <= 1.0


def test_full_analysis_impact_assessment_valid(client):
    data = client.post("/api/ai/full-analysis", json={"text": SAMPLE_TEXT}).json()
    impact = data["impact_assessment"]
    assert isinstance(impact["impact_score"], int)
    assert 0 <= impact["impact_score"] <= 100
    assert impact["impact_level"] in {"low", "medium", "high", "critical"}
    assert impact["reasoning"]


def test_full_analysis_uses_gateway_document_analysis(monkeypatch):
    gateway_document = analyze_document_legacy(SAMPLE_TEXT).model_copy(
        update={"title": "Gateway DocumentAnalysis"}
    )
    calls: list[str] = []

    def fake_gateway_analysis(text: str) -> DocumentAnalysis:
        calls.append(text)
        return gateway_document

    monkeypatch.setattr(
        "app.ai.service.analyze_document_with_gateway",
        fake_gateway_analysis,
    )

    result = full_ai_analysis(SAMPLE_TEXT)

    assert calls == [SAMPLE_TEXT]
    assert result.document_analysis.title == "Gateway DocumentAnalysis"
    assert result.impact_assessment.reasoning
    assert isinstance(result.client_relevance, list)
    assert isinstance(result.notification_drafts, list)


def test_full_analysis_falls_back_to_legacy_analysis(monkeypatch, caplog):
    def failing_gateway_analysis(_: str) -> DocumentAnalysis:
        raise LLMProviderUnavailableError(
            "gateway unavailable",
            provider="mock",
        )

    monkeypatch.setattr(
        "app.ai.service.analyze_document_with_gateway",
        failing_gateway_analysis,
    )

    with caplog.at_level(logging.ERROR, logger="app.ai.service"):
        result = full_ai_analysis(SAMPLE_TEXT)

    expected = analyze_document_legacy(SAMPLE_TEXT)
    assert result.document_analysis == expected
    assert result.analysis_metadata.fallback_used is True
    assert result.analysis_metadata.fallback_reason
    assert "LLMProviderUnavailableError" in result.analysis_metadata.fallback_reason
    assert "legacy mock fallback" in caplog.text


# --- POST /api/ai/document-analysis ---


def test_document_analysis_returns_200(client):
    response = client.post("/api/ai/document-analysis", json={"text": SAMPLE_TEXT})
    assert response.status_code == 200


def test_document_analysis_valid_schema(client):
    data = client.post("/api/ai/document-analysis", json={"text": SAMPLE_TEXT}).json()
    # Валидируем, что ответ соответствует DocumentAnalysis
    doc = DocumentAnalysis.model_validate(data)
    assert doc.title
    assert doc.short_summary
    assert isinstance(doc.topics, list)
    assert 0.0 <= doc.confidence <= 1.0


# --- POST /api/ai/gateway-test ---


def test_gateway_test_returns_200(client):
    response = client.post("/api/ai/gateway-test", json={"text": SAMPLE_TEXT})
    assert response.status_code == 200


def test_gateway_test_returns_valid_document_analysis(client):
    data = client.post("/api/ai/gateway-test", json={"text": SAMPLE_TEXT}).json()
    doc = DocumentAnalysis.model_validate(data)
    assert doc.title
    assert doc.short_summary


# --- POST /api/events/create-card ---


def test_create_card_returns_200(client):
    response = client.post("/api/events/create-card", json={"text": SAMPLE_TEXT})
    assert response.status_code == 200


def test_create_card_contains_event_card(client):
    data = client.post("/api/events/create-card", json={"text": SAMPLE_TEXT}).json()
    assert "event_card" in data
    card = data["event_card"]
    assert card["event_id"]
    assert card["review_state"] == "needs_review"
    assert isinstance(card["evidence_fragments"], list)
    assert isinstance(card["topics"], list)
    assert "impact_score" in card
    assert "impact_level" in card


# --- POST /api/events/create-card-from-document ---


def test_create_card_from_document_returns_200(client):
    payload = {
        "document_id": "doc-001",
        "version_id": "ver-001",
        "chunks": [
            {
                "chunk_id": "chunk-001",
                "text": SAMPLE_TEXT,
                "order_index": 1,
                "section_title": "Требования",
                "page_number": 1,
            }
        ],
        "metadata": {
            "title": "Проект требований к обработке ПДн",
            "source": "demo",
            "original_url": "https://example.org/doc-001",
        },
        "source_type": "uploaded_text",
    }
    response = client.post("/api/events/create-card-from-document", json=payload)
    assert response.status_code == 200
    card = response.json()["event_card"]
    assert card["event_id"]
    assert card["title"] == "Проект требований к обработке ПДн"
    assert isinstance(card["evidence_fragments"], list)
