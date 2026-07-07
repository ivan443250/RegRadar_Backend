"""Privacy, persistence and integration tests for the JSONL AI audit trail."""

import json

import httpx
import pytest

from app.ai.gateway.base import LLMRawResponse, LLMRequest
from app.ai.gateway.config import GatewayConfig
from app.ai.gateway.errors import (
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMResponseParsingError,
    LLMResponseValidationError,
)
from app.ai.gateway.gateway import LLMGateway
from app.ai.gateway.polza_provider import PolzaAIProvider
from app.ai.llm_call_logger import (
    LLMCallLogRecord,
    clear_llm_call_logs_for_tests,
    log_llm_call,
    read_recent_llm_calls,
)
from app.ai.mock_provider import analyze_document
from app.ai.schemas import DocumentAnalysis


@pytest.fixture(autouse=True)
def isolated_log_path(tmp_path, monkeypatch):
    path = tmp_path / "logs" / "llm_calls.jsonl"
    monkeypatch.setattr("app.ai.llm_call_logger.LOG_PATH", path)
    clear_llm_call_logs_for_tests()
    yield path
    clear_llm_call_logs_for_tests()


def _record(**updates):
    values = {
        "operation": "document_analysis",
        "provider": "mock",
        "runtime": "MOCK",
        "model": "mock-v1",
        "status": "success",
    }
    values.update(updates)
    return LLMCallLogRecord(**values)


def test_log_call_creates_valid_jsonl(isolated_log_path):
    record = _record()
    log_llm_call(record)
    assert isolated_log_path.exists()
    payload = json.loads(isolated_log_path.read_text(encoding="utf-8"))
    assert payload["call_id"] == record.call_id
    assert payload["provider"] == "mock"


def test_read_recent_returns_last_n():
    records = [_record(model=f"model-{index}") for index in range(3)]
    for record in records:
        log_llm_call(record)
    recent = read_recent_llm_calls(2)
    assert [record.model for record in recent] == ["model-1", "model-2"]


def test_error_message_is_truncated():
    record = _record(status="error", error_message="x" * 700)
    assert len(record.error_message or "") == 500


def test_error_message_redacts_credentials():
    record = _record(
        status="error",
        error_message=(
            "Authorization: Bearer top-secret-token "
            "POLZA_API_KEY=another-secret sk-abcdefghijk"
        ),
    )
    serialized = record.model_dump_json()
    assert "top-secret-token" not in serialized
    assert "another-secret" not in serialized
    assert "sk-abcdefghijk" not in serialized
    assert "POLZA_API_KEY" not in serialized


def test_sensitive_metadata_is_redacted(isolated_log_path):
    secret = "super-secret-api-key"
    log_llm_call(
        _record(
            metadata={
                "POLZA_API_KEY": secret,
                "document_text": "full private document",
                "prompt": "full prompt",
                "safe": "visible",
            }
        )
    )
    raw = isolated_log_path.read_text(encoding="utf-8")
    assert secret not in raw
    assert "POLZA_API_KEY" not in raw
    assert "document_text" not in raw
    assert "full private document" not in raw
    assert "full prompt" not in raw
    assert "visible" in raw


def test_mock_gateway_call_is_logged(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    gateway = LLMGateway()
    gateway.generate_structured(
        prompt="Требования к персональным данным.",
        response_model=DocumentAnalysis,
        metadata={
            "operation": "document_analysis",
            "input_chars": 34,
            "document_text": "Требования к персональным данным.",
        },
    )
    records = read_recent_llm_calls()
    assert records[-1].provider == "mock"
    assert records[-1].status == "success"
    assert records[-1].input_chars == 34


def test_polza_success_with_mocked_http_is_logged():
    document = analyze_document("Требования к персональным данным.")

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "provider/model",
                "choices": [{"message": {"content": document.model_dump_json()}}],
                "usage": {"total_tokens": 25},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    gateway = LLMGateway.__new__(LLMGateway)
    gateway._config = GatewayConfig(llm_provider="polza", polzaai_api_key="key")
    gateway._provider = PolzaAIProvider(api_key="key", client=client)
    gateway.last_warnings = []
    gateway.last_model = "provider/model"
    gateway.generate_structured(
        "safe prompt",
        DocumentAnalysis,
        metadata={"operation": "document_analysis", "input_chars": 20},
    )
    client.close()
    records = read_recent_llm_calls()
    assert records[-1].provider == "polza"
    assert records[-1].runtime == "POLZA"
    assert records[-1].status == "success"


@pytest.mark.parametrize(
    ("failure", "expected_error", "expected_status"),
    [
        ("invalid_json", LLMResponseParsingError, "validation_error"),
        ("invalid_schema", LLMResponseValidationError, "validation_error"),
        ("timeout", LLMProviderTimeoutError, "timeout"),
    ],
)
def test_gateway_failure_types_are_audited(
    failure,
    expected_error,
    expected_status,
):
    class FailingProvider:
        name = "polza"

        def complete(self, request: LLMRequest):
            if failure == "timeout":
                raise TimeoutError("deadline exceeded")
            return LLMRawResponse(
                raw_text=(
                    "not-json"
                    if failure == "invalid_json"
                    else '{"title":"missing required fields"}'
                ),
                model="provider/model",
                provider="polza",
            )

    gateway = LLMGateway.__new__(LLMGateway)
    gateway._config = GatewayConfig(llm_provider="polza", polza_max_retries=0)
    gateway._provider = FailingProvider()
    with pytest.raises(expected_error):
        gateway.generate_structured(
            "safe prompt",
            DocumentAnalysis,
            metadata={"operation": "document_analysis", "input_chars": 20},
        )
    record = read_recent_llm_calls()[-1]
    assert record.provider == "polza"
    assert record.status == expected_status
    assert record.error_type


def test_polza_error_and_mock_fallback_create_two_records(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza_with_fallback")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    monkeypatch.setenv("POLZA_MAX_RETRIES", "0")

    def fail(self, request: LLMRequest):
        raise LLMProviderUnavailableError("HTTP 503", provider="polza")

    monkeypatch.setattr(PolzaAIProvider, "complete", fail)
    response = client.post(
        "/api/ai/full-analysis",
        json={"text": "Требования к обработке персональных данных."},
    )
    assert response.status_code == 200
    records = read_recent_llm_calls()
    assert any(record.provider == "polza" and record.status == "error" for record in records)
    assert any(record.provider == "mock" and record.status == "fallback" for record in records)
    metadata = response.json()["analysis_metadata"]
    assert metadata["request_id"]
    assert len(metadata["llm_call_ids"]) >= 2


def test_rag_no_data_logs_skipped_and_empty_sources(client):
    response = client.post(
        "/api/rag/ask",
        json={"question": "Какая погода на Марсе?"},
    )
    data = response.json()
    assert response.status_code == 200
    assert data["no_data"] is True
    assert data["source_fragments"] == []
    record = read_recent_llm_calls()[-1]
    assert record.operation == "rag_answer"
    assert record.provider == "none"
    assert record.status == "skipped"
    assert record.metadata["reason"] == "no_source_fragments"


def test_relevant_rag_call_is_logged_without_fragments(client):
    response = client.post(
        "/api/rag/ask",
        json={
            "question": "Какой срок установлен для банка?",
            "source_fragments": [
                {
                    "text": "Банк обязан выполнить требования до 1 июля.",
                    "document_id": "doc-1",
                    "version_id": "v1",
                    "chunk_id": "chunk-1",
                }
            ],
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["no_data"] is False
    record = read_recent_llm_calls()[-1]
    assert record.operation == "rag_answer"
    assert record.prompt_version == "rag_answer_v1"
    assert "rag_fragments" not in record.metadata
    assert record.call_id in data["metadata"]["llm_call_ids"]


def test_language_retry_is_logged(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    source = "Организации обязаны соблюдать требования к персональным данным."
    baseline = analyze_document(source)
    english = baseline.model_copy(
        update={"short_summary": "This document introduces new requirements."}
    )
    responses = [english, baseline]
    calls = 0

    def sequenced(self, request: LLMRequest):
        nonlocal calls
        response = responses[calls]
        calls += 1
        return LLMRawResponse(
            raw_text=response.model_dump_json(),
            model=request.model or "provider/model",
            provider="polza",
        )

    monkeypatch.setattr(PolzaAIProvider, "complete", sequenced)
    response = client.post("/api/ai/full-analysis", json={"text": source})
    assert response.status_code == 200
    records = read_recent_llm_calls()
    assert [record.operation for record in records] == [
        "document_analysis",
        "language_retry",
    ]
    assert len(response.json()["analysis_metadata"]["llm_call_ids"]) == 2


def test_language_fallback_is_logged(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza_with_fallback")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    source = "Организации обязаны соблюдать требования к персональным данным."
    english = analyze_document(source).model_copy(
        update={"short_summary": "This document introduces new requirements."}
    )

    def english_response(self, request: LLMRequest):
        return LLMRawResponse(
            raw_text=english.model_dump_json(),
            model=request.model or "provider/model",
            provider="polza",
        )

    monkeypatch.setattr(PolzaAIProvider, "complete", english_response)
    response = client.post("/api/ai/full-analysis", json={"text": source})
    metadata = response.json()["analysis_metadata"]
    assert response.status_code == 200
    assert metadata["fallback_used"] is True
    records = read_recent_llm_calls()
    assert [record.operation for record in records] == [
        "document_analysis",
        "language_retry",
        "fallback",
    ]
    assert records[-1].runtime == "FALLBACK"
    assert records[-1].status == "fallback"
    assert len(metadata["llm_call_ids"]) == 3


def test_debug_endpoint_returns_recent_sanitized_records(client):
    log_llm_call(_record(request_id="request-1"))
    response = client.get("/api/debug/llm-calls?limit=20")
    assert response.status_code == 200
    records = response.json()
    assert records[-1]["request_id"] == "request-1"
    assert "api_key" not in response.text.casefold()


def test_debug_endpoint_returns_empty_list_without_log_file(client):
    clear_llm_call_logs_for_tests()
    response = client.get("/api/debug/llm-calls")
    assert response.status_code == 200
    assert response.json() == []


def test_debug_endpoint_rejects_limit_over_200(client):
    assert client.get("/api/debug/llm-calls?limit=201").status_code == 422


def test_log_write_error_does_not_break_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr("app.ai.llm_call_logger.LOG_PATH", tmp_path)
    log_llm_call(_record())
