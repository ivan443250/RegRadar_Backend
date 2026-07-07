"""Russian user-visible language guard and Polza retry/fallback tests."""

from app.ai.gateway.base import LLMRequest, LLMRawResponse
from app.ai.gateway.polza_provider import PolzaAIProvider
from app.ai.language_guard import (
    is_mostly_russian_text,
    validate_document_analysis_language,
)
from app.ai.mock_provider import analyze_document as baseline_analysis


SOURCE_TEXT = (
    "Указ Президента Российской Федерации регулирует рынок ценных бумаг. "
    "Документ вступает в силу со дня опубликования."
)


def _raw_response(document, request: LLMRequest) -> LLMRawResponse:
    return LLMRawResponse(
        raw_text=document.model_dump_json(),
        model=request.model or "provider/model",
        provider="polza",
    )


def _english_document():
    return baseline_analysis(SOURCE_TEXT).model_copy(
        update={
            "title": "Presidential Decree No. 469",
            "short_summary": (
                "Presidential Decree regulates the securities market and "
                "takes effect on publication."
            ),
        }
    )


def test_language_guard_accepts_russian_document_analysis():
    document = baseline_analysis(SOURCE_TEXT)
    assert validate_document_analysis_language(document) == []


def test_language_guard_ignores_short_technical_abbreviations():
    assert is_mostly_russian_text(
        "API, PDF, JSON, URL и ID используются во внутренней системе."
    )
    assert is_mostly_russian_text("no-match")


def test_language_guard_reports_english_visible_fields():
    document = _english_document().model_copy(update={"status": "effective"})
    warnings = validate_document_analysis_language(document)
    assert "LLM returned non-Russian title" in warnings
    assert "LLM returned non-Russian short_summary" in warnings
    assert "LLM returned non-Russian status" in warnings


def test_russian_polza_json_passes_without_language_retry(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    calls: list[LLMRequest] = []

    def russian_response(self, request: LLMRequest):
        calls.append(request)
        return _raw_response(baseline_analysis(SOURCE_TEXT), request)

    monkeypatch.setattr(PolzaAIProvider, "complete", russian_response)
    response = client.post("/api/ai/full-analysis", json={"text": SOURCE_TEXT})
    metadata = response.json()["analysis_metadata"]

    assert response.status_code == 200
    assert len(calls) == 1
    assert metadata["fallback_used"] is False
    assert "LLM language retry was used" not in metadata["warnings"]


def test_english_summary_is_retried_and_corrected(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    responses = [_english_document(), baseline_analysis(SOURCE_TEXT)]
    requests: list[LLMRequest] = []

    def sequenced_response(self, request: LLMRequest):
        requests.append(request)
        return _raw_response(responses[len(requests) - 1], request)

    monkeypatch.setattr(PolzaAIProvider, "complete", sequenced_response)
    response = client.post("/api/ai/full-analysis", json={"text": SOURCE_TEXT})
    data = response.json()

    assert response.status_code == 200
    assert len(requests) == 2
    assert "Предыдущий ответ содержит английский текст" in requests[1].metadata[
        "additional_user_message"
    ]
    assert data["analysis_metadata"]["fallback_used"] is False
    assert "LLM language retry was used" in data["analysis_metadata"]["warnings"]
    assert is_mostly_russian_text(data["document_analysis"]["short_summary"])
    assert data["document_analysis"]["source_fragments"]
    assert all(
        fragment in SOURCE_TEXT
        for fragment in data["document_analysis"]["source_fragments"]
    )


def test_persistent_english_summary_uses_safe_fallback(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza_with_fallback")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    calls = 0

    def english_response(self, request: LLMRequest):
        nonlocal calls
        calls += 1
        return _raw_response(_english_document(), request)

    monkeypatch.setattr(PolzaAIProvider, "complete", english_response)
    response = client.post("/api/ai/full-analysis", json={"text": SOURCE_TEXT})
    data = response.json()
    metadata = data["analysis_metadata"]

    assert response.status_code == 200
    assert calls == 2
    assert metadata["fallback_used"] is True
    assert metadata["fallback_reason"] == (
        "LLM returned non-Russian user-visible fields"
    )
    assert "LLM returned non-Russian short_summary" in metadata["warnings"]
    assert is_mostly_russian_text(data["document_analysis"]["short_summary"])
    assert data["document_analysis"]["source_fragments"]
    assert all(
        fragment in SOURCE_TEXT
        for fragment in data["document_analysis"]["source_fragments"]
    )
