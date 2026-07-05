"""PolzaAI boundary tests. No test in this module performs real HTTP."""

import json

import httpx
import pytest

from app.ai.gateway.base import LLMRequest, LLMRawResponse
from app.ai.gateway.config import GatewayConfig
from app.ai.gateway.errors import (
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMResponseParsingError,
    LLMResponseValidationError,
)
from app.ai.gateway.gateway import LLMGateway, extract_json_object
from app.ai.gateway.polza_provider import PolzaAIProvider
from app.ai.mock_provider import analyze_document as baseline_analysis
from app.ai.schemas import DocumentAnalysis


def _polza_response_for(self, request: LLMRequest) -> LLMRawResponse:
    text = str(request.metadata.get("document_text", request.prompt))
    return LLMRawResponse(
        raw_text=f"```json\n{baseline_analysis(text).model_dump_json()}\n```",
        model=request.model or "provider/model",
        provider="polza",
    )


@pytest.mark.parametrize(
    ("raw", "warning_fragment"),
    [
        ('{"value": 1}', None),
        ('```json\n{"value": 1}\n```', "code fence"),
        ('Result follows: {"value": 1} done', "surrounding"),
    ],
)
def test_json_extraction_handles_common_model_output(raw, warning_fragment):
    parsed, warning = extract_json_object(raw)
    assert parsed == {"value": 1}
    if warning_fragment is None:
        assert warning is None
    else:
        assert warning_fragment in (warning or "")


def test_json_extraction_rejects_missing_object():
    with pytest.raises(LLMResponseParsingError):
        extract_json_object("there is no JSON here")


def test_polza_provider_maps_timeout_without_network():
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("deadline", request=request)

    client = httpx.Client(transport=httpx.MockTransport(timeout))
    provider = PolzaAIProvider(api_key="key", client=client)
    with pytest.raises(LLMProviderTimeoutError):
        provider.complete(LLMRequest(prompt="test", model="model"))
    client.close()


def test_polza_provider_maps_http_error_without_network():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(503, text="unavailable")
        )
    )
    provider = PolzaAIProvider(api_key="key", client=client)
    with pytest.raises(LLMProviderUnavailableError, match="HTTP 503"):
        provider.complete(LLMRequest(prompt="test", model="model"))
    client.close()


@pytest.mark.parametrize(
    ("raw_text", "error_type"),
    [
        ("invalid JSON", LLMResponseParsingError),
        ('{"title": "missing required fields"}', LLMResponseValidationError),
    ],
)
def test_gateway_retries_invalid_structured_responses(raw_text, error_type):
    class InvalidProvider:
        name = "polza"

        def __init__(self):
            self.calls = 0

        def complete(self, request: LLMRequest) -> LLMRawResponse:
            self.calls += 1
            return LLMRawResponse(
                raw_text=raw_text,
                model="provider/model",
                provider="polza",
            )

    provider = InvalidProvider()
    gateway = LLMGateway.__new__(LLMGateway)
    gateway._config = GatewayConfig(llm_provider="mock", llm_max_retries=1)
    gateway._provider = provider
    gateway.last_warnings = []
    gateway.last_model = "provider/model"

    with pytest.raises(error_type):
        gateway.generate_structured("test", DocumentAnalysis)
    assert provider.calls == 2


def test_full_analysis_polza_success_metadata(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    monkeypatch.setenv("POLZA_MODEL", "provider/model")
    monkeypatch.setattr(PolzaAIProvider, "complete", _polza_response_for)

    response = client.post(
        "/api/ai/full-analysis",
        json={"text": "Требования к обработке персональных данных."},
    )

    assert response.status_code == 200
    metadata = response.json()["analysis_metadata"]
    assert metadata["analysis_provider"] == "polza"
    assert metadata["provider"] == "polza"
    assert metadata["processing_mode"] == "gateway_polza"
    assert metadata["model_version"] == "provider/model"
    assert metadata["fallback_used"] is False
    assert "code fence" in " ".join(metadata["warnings"])


@pytest.mark.parametrize("failure_kind", ["http", "json", "validation"])
def test_full_analysis_falls_back_for_polza_failures(
    client,
    monkeypatch,
    failure_kind,
):
    monkeypatch.setenv("LLM_PROVIDER", "polza_with_fallback")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    monkeypatch.setenv("POLZA_MAX_RETRIES", "0")

    def failing_response(self, request: LLMRequest) -> LLMRawResponse:
        if failure_kind == "http":
            raise LLMProviderUnavailableError("HTTP 503", provider="polza")
        return LLMRawResponse(
            raw_text=(
                "not-json"
                if failure_kind == "json"
                else '{"title":"schema mismatch"}'
            ),
            model="provider/model",
            provider="polza",
        )

    monkeypatch.setattr(PolzaAIProvider, "complete", failing_response)
    response = client.post(
        "/api/ai/full-analysis",
        json={"text": "Нейтральный материал о мероприятии."},
    )

    assert response.status_code == 200
    metadata = response.json()["analysis_metadata"]
    assert metadata["fallback_used"] is True
    assert metadata["processing_mode"] == "gateway_polza_with_fallback"
    assert "Falling back to MockProvider" in metadata["warnings"]


def test_missing_polza_key_falls_back_with_metadata(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza_with_fallback")
    monkeypatch.delenv("POLZA_API_KEY", raising=False)
    monkeypatch.delenv("POLZAAI_API_KEY", raising=False)

    response = client.post(
        "/api/ai/full-analysis",
        json={"text": "Нейтральный материал о проведенном мероприятии."},
    )

    assert response.status_code == 200
    data = response.json()
    metadata = data["analysis_metadata"]
    assert metadata["analysis_provider"] == "polza"
    assert metadata["processing_mode"] == "gateway_polza_with_fallback"
    assert metadata["fallback_used"] is True
    assert "POLZA_API_KEY" in " ".join(metadata["warnings"])
    assert data["client_relevance"] == []
    assert data["notification_drafts"] == []


def test_document_analysis_endpoint_survives_missing_key(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza")
    monkeypatch.delenv("POLZA_API_KEY", raising=False)
    response = client.post(
        "/api/ai/document-analysis",
        json={"text": "Документ о персональных данных."},
    )
    assert response.status_code == 200
    assert response.json()["title"]


def test_upload_create_card_survives_polza_timeout(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    monkeypatch.setenv("POLZA_MAX_RETRIES", "0")

    def timeout(self, request):
        raise LLMProviderTimeoutError("deadline", provider="polza")

    monkeypatch.setattr(PolzaAIProvider, "complete", timeout)
    response = client.post(
        "/api/documents/upload-create-card",
        files={
            "file": (
                "document.txt",
                "Документ о персональных данных.".encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    metadata = response.json()["card"]["event_card"]["analysis_metadata"]
    assert metadata["fallback_used"] is True
    assert metadata["analysis_provider"] == "polza"


def test_controlled_baseline_overrides_llm_domain_for_no_match(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")

    def unsafe_domain_response(request: LLMRequest) -> LLMRawResponse:
        text = str(request.metadata["document_text"])
        document = baseline_analysis(text).model_copy(
            update={"domain": "personal_data", "topics": ["персональные данные"]}
        )
        return LLMRawResponse(
            raw_text=document.model_dump_json(),
            model="provider/model",
            provider="polza",
        )

    monkeypatch.setattr(PolzaAIProvider, "complete", unsafe_domain_response)
    response = client.post(
        "/api/ai/full-analysis",
        json={
            "text": "Информация о спортивном мероприятии.",
            "client_profiles": [
                {
                    "client_id": "pd-client",
                    "company_name": "ООО Данные",
                    "tags": ["personal_data"],
                }
            ],
        },
    )
    data = response.json()
    assert data["document_analysis"]["domain"] == "neutral_no_match"
    assert data["client_relevance"] == []
    assert data["notification_drafts"] == []
