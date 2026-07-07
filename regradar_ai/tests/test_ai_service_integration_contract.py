"""External-backend and FastAPI dependency contract for the AI facade."""

import asyncio
import inspect

import pytest
from fastapi.testclient import TestClient

from app import main
from app.ai.reg_radar_ai_service import (
    CreateEventCardInput,
    RegRadarAIService,
)
from app.ai.schemas import AIModelsResponse
from app.ai.gateway.config import reset_config
from app.ai.service_factory import (
    build_reg_radar_ai_service,
    get_reg_radar_ai_service,
    reset_reg_radar_ai_service_for_tests,
)
from app.storage import (
    document_repository,
    event_repository,
    notification_repository,
    rag_chat_repository,
)


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(document_repository, "DOCUMENTS_PATH", tmp_path / "documents.jsonl")
    monkeypatch.setattr(document_repository, "CHUNKS_PATH", tmp_path / "chunks.jsonl")
    monkeypatch.setattr(event_repository, "EVENTS_PATH", tmp_path / "events.jsonl")
    monkeypatch.setattr(notification_repository, "NOTIFICATIONS_PATH", tmp_path / "notifications.jsonl")
    monkeypatch.setattr(rag_chat_repository, "RAG_CHATS_PATH", tmp_path / "rag_chats.jsonl")
    monkeypatch.setattr("app.ai.llm_call_logger.LOG_PATH", tmp_path / "llm_calls.jsonl")
    reset_config()
    reset_reg_radar_ai_service_for_tests()
    yield
    main.app.dependency_overrides.clear()
    reset_config()
    reset_reg_radar_ai_service_for_tests()


def test_factory_returns_singleton_and_builder_returns_fresh_service():
    reset_reg_radar_ai_service_for_tests()
    first = get_reg_radar_ai_service()
    second = get_reg_radar_ai_service()
    fresh = build_reg_radar_ai_service()
    assert first is second
    assert fresh is not first


def test_external_backend_can_use_only_facade():
    service = build_reg_radar_ai_service()
    result = asyncio.run(
        service.create_event_card(
            CreateEventCardInput(
                text="Организации обязаны соблюдать требования 152-ФЗ.",
                document_id="external-doc",
                version_id="v1",
                request_id="external-request",
            )
        )
    )
    assert result.analysis_metadata.context_document_id == "external-doc"
    assert result.analysis_metadata.request_id == "external-request"
    assert result.document_analysis
    assert result.impact_assessment


def test_fastapi_models_endpoint_uses_dependency_injected_facade():
    class SpyService(RegRadarAIService):
        def __init__(self):
            super().__init__()
            self.called = False

        def get_models(self):
            self.called = True
            return AIModelsResponse(
                provider="spy",
                default_model="spy/model",
                allowed_models=[],
            )

    spy = SpyService()
    main.app.dependency_overrides[get_reg_radar_ai_service] = lambda: spy
    try:
        with TestClient(main.app) as client:
            response = client.get("/api/ai/models")
    finally:
        main.app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["provider"] == "spy"
    assert spy.called is True


def test_primary_routes_delegate_to_service_facade():
    route_functions = (
        main.document_analysis_via_gateway,
        main.ai_full_analysis,
        main.upload_document_analysis,
        main.upload_create_event_card,
        main.create_regulatory_event_card_from_document,
        main.rag_ask,
        main.mock_send_notification,
        main.ai_models,
    )
    for route_function in route_functions:
        source = inspect.getsource(route_function)
        assert "service." in source
        assert "PolzaAIProvider" not in source
        assert "MockLLMProvider" not in source


def test_ai_health_endpoint_contract(client):
    response = client.get("/api/ai/health")
    data = response.json()
    assert response.status_code == 200
    assert data["status"] in {"ok", "degraded"}
    assert data["provider_mode"]
    assert data["default_model"]
    assert set(data["storage"]) == {
        "documents",
        "chunks",
        "events",
        "rag_chats",
        "notifications",
    }
    assert data["prompts"] == {
        "document_analysis_v1": "ok",
        "rag_answer_v1": "ok",
    }
