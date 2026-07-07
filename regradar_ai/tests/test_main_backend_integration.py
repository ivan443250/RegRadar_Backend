"""FastAPI and HTTP-adapter tests for main backend integration."""

import asyncio

import httpx
import pytest

from app import main
from app.ai.gateway.config import reset_config
from app.ai.llm_call_logger import clear_llm_call_logs_for_tests
from app.ai.service_factory import reset_reg_radar_ai_service_for_tests
from app.ai.reg_radar_ai_service import RegRadarAIService
from app.integrations.main_backend.client import MainBackendApiClient
from app.integrations.main_backend.router import get_main_backend_client
from app.integrations.main_backend.service import MainBackendIntegrationService
from app.storage import (
    document_repository,
    event_repository,
    notification_repository,
    rag_chat_repository,
)


PROFILE = {
    "id": "main-personal-1",
    "companyName": "ООО Персональные сервисы",
    "okved": "62.01",
    "industry": "it",
    "size": 2,
    "hasForeignTrade": False,
    "usesOnlinePayments": True,
    "handlesPersonalData": True,
    "cashOperationsLevel": 0,
    "riskProfile": 1,
    "bankSegment": "SME",
}


def request_payload(*, profiles=...):
    payload = {
        "document": {
            "id": "main-document-1",
            "title": "Требования к персональным данным",
            "text": (
                "Организации обязаны соблюдать требования 152-ФЗ к обработке "
                "персональных данных и хранить согласия клиентов."
            ),
            "originalUrl": "https://example.test/document-1",
            "regulator": "Роскомнадзор",
            "documentType": 1,
            "publicationDate": "2026-07-01",
        },
        "modelOverride": None,
        "requestId": "main-request-1",
    }
    if profiles is not ...:
        payload["clientProfiles"] = profiles
    return payload


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.delenv("MAIN_BACKEND_URL", raising=False)
    monkeypatch.delenv("MAIN_BACKEND_ALLOW_SEED_FALLBACK", raising=False)
    monkeypatch.setattr(document_repository, "DOCUMENTS_PATH", tmp_path / "documents.jsonl")
    monkeypatch.setattr(document_repository, "CHUNKS_PATH", tmp_path / "chunks.jsonl")
    monkeypatch.setattr(event_repository, "EVENTS_PATH", tmp_path / "events.jsonl")
    monkeypatch.setattr(notification_repository, "NOTIFICATIONS_PATH", tmp_path / "notifications.jsonl")
    monkeypatch.setattr(rag_chat_repository, "RAG_CHATS_PATH", tmp_path / "rag_chats.jsonl")
    monkeypatch.setattr("app.ai.llm_call_logger.LOG_PATH", tmp_path / "llm_calls.jsonl")
    reset_config()
    reset_reg_radar_ai_service_for_tests()
    clear_llm_call_logs_for_tests()
    yield
    main.app.dependency_overrides.clear()
    reset_config()
    reset_reg_radar_ai_service_for_tests()
    clear_llm_call_logs_for_tests()


def test_analyze_document_endpoint_with_request_profiles(client):
    response = client.post(
        "/api/integration/main-backend/analyze-document",
        json=request_payload(profiles=[PROFILE]),
    )
    data = response.json()
    assert response.status_code == 200
    assert data["documentId"] == "main-document-1"
    assert data["regulatoryEvent"]["documentId"] == "main-document-1"
    assert data["clientImpacts"][0]["clientProfileId"] == "main-personal-1"
    assert data["notificationDrafts"]
    assert data["evidence"]
    assert data["ragContext"]["documentId"] == "main-document-1"
    assert data["aiMetadata"]["provider"] == "mock"
    assert data["aiMetadata"]["request_id"] == "main-request-1"
    assert data["aiMetadata"]["llm_call_ids"]


def test_missing_profiles_are_loaded_via_main_backend_client(client):
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/clientprofiles"
        return httpx.Response(200, json=[PROFILE])

    async_client = httpx.AsyncClient(
        base_url="http://main-backend:8080",
        transport=httpx.MockTransport(handler),
    )
    adapter = MainBackendApiClient(
        "http://main-backend:8080",
        client=async_client,
    )
    main.app.dependency_overrides[get_main_backend_client] = lambda: adapter
    try:
        response = client.post(
            "/api/integration/main-backend/analyze-document",
            json=request_payload(),
        )
    finally:
        main.app.dependency_overrides.pop(get_main_backend_client, None)
        asyncio.run(async_client.aclose())
    assert response.status_code == 200
    assert response.json()["clientImpacts"][0]["clientProfileId"] == "main-personal-1"


def test_unavailable_main_backend_without_request_profiles_is_clear_error(client):
    async def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async_client = httpx.AsyncClient(
        base_url="http://main-backend:8080",
        transport=httpx.MockTransport(unavailable),
    )
    adapter = MainBackendApiClient(
        "http://main-backend:8080",
        client=async_client,
    )
    main.app.dependency_overrides[get_main_backend_client] = lambda: adapter
    try:
        response = client.post(
            "/api/integration/main-backend/analyze-document",
            json=request_payload(),
        )
    finally:
        main.app.dependency_overrides.pop(get_main_backend_client, None)
        asyncio.run(async_client.aclose())
    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"]


def test_no_url_and_no_profiles_does_not_silently_use_seed(client):
    response = client.post(
        "/api/integration/main-backend/analyze-document",
        json=request_payload(),
    )
    assert response.status_code == 503
    assert "clientProfiles" in response.json()["detail"]


def test_explicit_empty_profiles_do_not_fetch_or_silently_use_seed(client):
    response = client.post(
        "/api/integration/main-backend/analyze-document",
        json=request_payload(profiles=[]),
    )
    assert response.status_code == 400
    assert "clientProfiles is empty" in response.json()["detail"]


def test_empty_document_text_returns_400(client):
    payload = request_payload(profiles=[PROFILE])
    payload["document"]["text"] = "   "
    response = client.post(
        "/api/integration/main-backend/analyze-document",
        json=payload,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "document.text must not be empty"


def test_integration_health_without_url_is_safe_and_does_not_call_llm(client, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("integration health must not call an LLM")

    monkeypatch.setattr(
        "app.ai.gateway.polza_provider.PolzaAIProvider.complete",
        forbidden,
    )
    response = client.get("/api/integration/main-backend/health")
    data = response.json()
    assert response.status_code == 200
    assert data["mainBackendUrl"] is None
    assert data["mainBackendReachable"] is False
    assert data["aiServiceHealth"]["status"] in {"ok", "degraded"}
    assert any("MAIN_BACKEND_URL" in note for note in data["notes"])


def test_client_profiles_debug_endpoint_uses_mocked_http_client(client):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[PROFILE])

    async_client = httpx.AsyncClient(
        base_url="http://main-backend:8080",
        transport=httpx.MockTransport(handler),
    )
    adapter = MainBackendApiClient(
        "http://main-backend:8080",
        client=async_client,
    )
    main.app.dependency_overrides[get_main_backend_client] = lambda: adapter
    try:
        response = client.get("/api/integration/main-backend/client-profiles")
    finally:
        main.app.dependency_overrides.pop(get_main_backend_client, None)
        asyncio.run(async_client.aclose())
    data = response.json()
    assert response.status_code == 200
    assert data["mainProfiles"][0]["companyName"] == "ООО Персональные сервисы"
    assert "personal_data" in data["aiProfiles"][0]["tags"]


def test_existing_document_loads_text_from_final_backend_read_api():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/documents/main-document-1":
            return httpx.Response(
                200,
                json={
                    "id": "main-document-1",
                    "sourceId": None,
                    "title": "Документ из backend",
                    "originalUrl": None,
                    "regulator": None,
                    "documentType": "Law",
                    "publicationDate": None,
                    "status": "Active",
                    "processingStatus": "AwaitingAi",
                    "createdAt": "2026-07-05T10:00:00Z",
                },
            )
        if request.url.path == "/api/documents/main-document-1/text":
            return httpx.Response(
                200,
                json={
                    "text": "Требования 152-ФЗ к обработке персональных данных."
                },
            )
        if request.url.path == "/api/clientprofiles":
            return httpx.Response(200, json=[PROFILE])
        raise AssertionError(f"Unexpected path: {request.url.path}")

    async_client = httpx.AsyncClient(
        base_url="http://main-backend:8080",
        transport=httpx.MockTransport(handler),
    )
    adapter = MainBackendApiClient(
        "http://main-backend:8080",
        client=async_client,
    )
    service = MainBackendIntegrationService(RegRadarAIService(), adapter)
    result = asyncio.run(service.analyze_existing_document_id("main-document-1"))
    asyncio.run(async_client.aclose())
    assert result.document_id == "main-document-1"
    assert result.regulatory_event.title == "Документ из backend"


def test_main_backend_client_reads_and_orders_chunks():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/documents/doc-1/chunks"
        return httpx.Response(
            200,
            json=[
                {"id": "chunk-2", "chunkIndex": 1, "content": "Второй", "tokenCount": 1},
                {"id": "chunk-1", "chunkIndex": 0, "content": "Первый", "tokenCount": 1},
            ],
        )

    async_client = httpx.AsyncClient(
        base_url="http://api:8080",
        transport=httpx.MockTransport(handler),
    )
    adapter = MainBackendApiClient("http://api:8080", client=async_client)
    chunks = asyncio.run(adapter.get_document_chunks("doc-1"))
    asyncio.run(async_client.aclose())
    assert [item.id for item in chunks] == ["chunk-1", "chunk-2"]


def test_main_backend_client_accepts_plain_text_document_content():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/documents/doc-plain/text"
        return httpx.Response(
            200,
            text="Нормализованный текст документа.",
            headers={"content-type": "text/plain; charset=utf-8"},
        )

    async_client = httpx.AsyncClient(
        base_url="http://api:8080",
        transport=httpx.MockTransport(handler),
    )
    adapter = MainBackendApiClient("http://api:8080", client=async_client)
    text = asyncio.run(adapter.get_document_text("doc-plain"))
    asyncio.run(async_client.aclose())
    assert text == "Нормализованный текст документа."
