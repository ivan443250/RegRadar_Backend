"""Backend-owned model catalog, allowlist and request override tests."""

from app.ai.gateway.base import LLMRequest, LLMRawResponse
from app.ai.gateway.errors import LLMProviderUnavailableError
from app.ai.gateway.polza_provider import PolzaAIProvider
from app.ai.mock_provider import analyze_document as baseline_analysis


MODEL = "deepseek/deepseek-v4-flash"


def _successful_polza(self, request: LLMRequest) -> LLMRawResponse:
    text = str(request.metadata["document_text"])
    return LLMRawResponse(
        raw_text=baseline_analysis(text).model_dump_json(),
        model=request.model or "unknown",
        provider="polza",
    )


def test_models_endpoint_returns_default_allowlist(client):
    response = client.get("/api/ai/models")
    data = response.json()

    assert response.status_code == 200
    assert data["provider"] == "mock"
    assert data["default_model"] == "openai/gpt-4o"
    assert [model["id"] for model in data["allowed_models"]] == [
        "deepseek/deepseek-v4-flash",
        "openai/gpt-4o",
        "qwen/qwen3.6-plus",
        "qwen/qwen3.5-flash-02-23",
    ]


def test_models_endpoint_reads_default_and_allowlist_from_env(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza_with_fallback")
    monkeypatch.setenv("POLZA_MODEL", "vendor/default")
    monkeypatch.setenv("POLZA_ALLOWED_MODELS", "vendor/default,vendor/fast")

    data = client.get("/api/ai/models").json()

    assert data["provider"] == "polza_with_fallback"
    assert data["default_model"] == "vendor/default"
    assert [model["id"] for model in data["allowed_models"]] == [
        "vendor/default",
        "vendor/fast",
    ]


def test_invalid_polza_model_returns_400_before_provider_call(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    calls: list[str] = []

    def should_not_run(self, request):
        calls.append(request.model or "")
        return _successful_polza(self, request)

    monkeypatch.setattr(PolzaAIProvider, "complete", should_not_run)
    response = client.post(
        "/api/ai/full-analysis",
        json={"text": "Документ о данных.", "model_override": "evil/model"},
    )

    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]
    assert calls == []


def test_mock_mode_ignores_override_without_breaking_request(client):
    response = client.post(
        "/api/ai/full-analysis",
        json={"text": "Нейтральный документ.", "model_override": "any/model"},
    )
    metadata = response.json()["analysis_metadata"]

    assert response.status_code == 200
    assert metadata["provider"] == "mock"
    assert metadata["selected_model"] == "any/model"
    assert metadata["model_version"] == "mock-reg-radar-v1"


def test_model_override_reaches_polza_and_metadata(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    models: list[str | None] = []

    def capture_model(self, request):
        models.append(request.model)
        return _successful_polza(self, request)

    monkeypatch.setattr(PolzaAIProvider, "complete", capture_model)
    response = client.post(
        "/api/ai/full-analysis",
        json={"text": "Документ о данных.", "model_override": MODEL},
    )
    metadata = response.json()["analysis_metadata"]

    assert response.status_code == 200
    assert models == [MODEL]
    assert metadata["selected_model"] == MODEL
    assert metadata["model_version"] == MODEL


def test_fallback_preserves_selected_model(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza_with_fallback")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    monkeypatch.setenv("POLZA_MAX_RETRIES", "0")

    def unavailable(self, request):
        raise LLMProviderUnavailableError("offline", provider="polza")

    monkeypatch.setattr(PolzaAIProvider, "complete", unavailable)
    response = client.post(
        "/api/ai/full-analysis",
        json={"text": "Документ о данных.", "model_override": MODEL},
    )
    metadata = response.json()["analysis_metadata"]

    assert response.status_code == 200
    assert metadata["fallback_used"] is True
    assert metadata["selected_model"] == MODEL
    assert metadata["model_version"] == MODEL


def test_upload_create_card_accepts_model_override(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={
            "file": (
                "document.txt",
                "Документ о персональных данных.".encode(),
                "text/plain",
            )
        },
        data={"model_override": MODEL},
    )
    metadata = response.json()["card"]["event_card"]["analysis_metadata"]

    assert response.status_code == 200
    assert metadata["provider"] == "mock"
    assert metadata["selected_model"] == MODEL


def test_upload_analysis_accepts_model_override(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("document.txt", "Документ.".encode(), "text/plain")},
        data={"model_override": MODEL},
    )
    metadata = response.json()["analysis_result"]["analysis_metadata"]
    assert response.status_code == 200
    assert metadata["selected_model"] == MODEL


def test_event_card_json_flows_accept_model_override(client):
    direct = client.post(
        "/api/events/create-card",
        json={"text": "Документ.", "model_override": MODEL},
    )
    from_document = client.post(
        "/api/events/create-card-from-document",
        json={
            "document_id": "doc-1",
            "version_id": "v1",
            "chunks": [
                {"chunk_id": "chunk-1", "text": "Документ.", "order_index": 0}
            ],
            "metadata": {},
            "model_override": MODEL,
        },
    )

    assert direct.status_code == 200
    assert from_document.status_code == 200
    assert direct.json()["event_card"]["analysis_metadata"]["selected_model"] == MODEL
    assert from_document.json()["event_card"]["analysis_metadata"]["selected_model"] == MODEL


def test_document_analysis_rejects_invalid_override_in_polza_mode(
    client,
    monkeypatch,
):
    monkeypatch.setenv("LLM_PROVIDER", "polza")
    response = client.post(
        "/api/ai/document-analysis",
        json={"text": "Документ.", "model_override": "invalid/model"},
    )
    assert response.status_code == 400
