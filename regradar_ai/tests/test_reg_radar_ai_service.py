"""Unit/integration coverage for the stable RegRadarAIService facade."""

import asyncio

import pytest

from app.ai.gateway.base import LLMRequest
from app.ai.gateway.config import reset_config
from app.ai.gateway.errors import LLMProviderUnavailableError
from app.ai.gateway.polza_provider import PolzaAIProvider
from app.ai.llm_call_logger import clear_llm_call_logs_for_tests
from app.ai.reg_radar_ai_service import (
    AnalyzeDocumentInput,
    CreateEventCardInput,
    CreateNotificationsInput,
    FullAnalysisInput,
    MockSendNotificationInput,
    RagAskInput,
    RegRadarAIService,
)
from app.ai.schemas import FullAIAnalysisResponse, RegulatoryEventCard
from app.ai.service_factory import build_reg_radar_ai_service
from app.storage import (
    document_repository,
    event_repository,
    notification_repository,
    rag_chat_repository,
)


TEXT = (
    "Организации обязаны соблюдать требования 152-ФЗ к обработке персональных "
    "данных и хранить согласия клиентов."
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
    clear_llm_call_logs_for_tests()
    yield
    reset_config()
    clear_llm_call_logs_for_tests()


def run(awaitable):
    return asyncio.run(awaitable)


def test_service_analyze_document_in_mock_mode():
    service = build_reg_radar_ai_service()
    result = run(service.analyze_document(AnalyzeDocumentInput(text=TEXT)))
    assert result.title
    assert result.source_fragments
    assert result.domain == "personal_data"


def test_service_full_analysis_contract_and_metadata():
    service = build_reg_radar_ai_service()
    result = run(
        service.run_full_analysis(
            FullAnalysisInput(
                text=TEXT,
                document_id="service-doc",
                request_id="request-123",
            )
        )
    )
    assert isinstance(result, FullAIAnalysisResponse)
    assert result.analysis_metadata.request_id == "request-123"
    assert result.analysis_metadata.context_document_id == "service-doc"
    assert result.analysis_metadata.llm_call_ids
    assert result.analysis_metadata.document_saved is True
    assert result.analysis_metadata.chunks_saved > 0


def test_service_create_event_card_returns_complete_card():
    service = RegRadarAIService()
    card = run(
        service.create_event_card(
            CreateEventCardInput(
                text=TEXT,
                document_id="card-doc",
                title="Внешний заголовок",
                request_id="card-request",
            )
        )
    )
    assert isinstance(card, RegulatoryEventCard)
    assert card.title == "Внешний заголовок"
    assert card.impact_score >= 0
    assert card.evidence_fragments
    assert card.analysis_metadata.request_id == "card-request"
    assert card.analysis_metadata.event_saved is True


def test_service_rag_unknown_and_persisted_document():
    service = RegRadarAIService()
    unknown = run(
        service.ask_rag(
            RagAskInput(question="Какой срок?", document_id="unknown")
        )
    )
    assert unknown.no_data is True
    run(
        service.run_full_analysis(
            FullAnalysisInput(text=TEXT, document_id="rag-doc")
        )
    )
    answer = run(
        service.ask_rag(
            RagAskInput(
                question="Что должны соблюдать организации?",
                document_id="rag-doc",
            )
        )
    )
    assert answer.no_data is False
    assert answer.source_fragments
    assert answer.metadata.rag_chat_saved is True


def test_service_create_notifications_keeps_only_relevant_safe_drafts():
    service = RegRadarAIService()
    card = run(
        service.create_event_card(
            CreateEventCardInput(text=TEXT, document_id="notification-doc")
        )
    )
    drafts = run(
        service.create_notifications(
            CreateNotificationsInput(
                event_card=card,
                client_relevance=card.client_relevance,
                document_analysis=card.document_analysis,
            )
        )
    )
    assert drafts
    assert {draft.client_id for draft in drafts} <= {
        client.client_id for client in card.client_relevance
    }
    assert all(draft.disclaimer for draft in drafts)


def test_service_mock_send_notification():
    service = RegRadarAIService()
    analysis = run(
        service.run_full_analysis(
            FullAnalysisInput(text=TEXT, document_id="delivery-doc")
        )
    )
    draft = analysis.notification_drafts[0]
    response = run(
        service.mock_send_notification(
            MockSendNotificationInput(
                notification_id=draft.notification_id,
                document_id="delivery-doc",
                client_id=draft.client_id,
                client_name=draft.client_name,
                notification=draft,
                request_id="delivery-request",
            )
        )
    )
    assert response.status == "sent_mock"
    assert response.saved is True
    assert response.metadata["request_id"] == "delivery-request"
    assert response.metadata["notification_saved"] is True


def test_service_models_and_health_do_not_call_provider(monkeypatch):
    def forbidden_call(self, request: LLMRequest):
        raise AssertionError("healthcheck must not call a paid provider")

    monkeypatch.setattr(PolzaAIProvider, "complete", forbidden_call)
    service = RegRadarAIService()
    models = service.get_models()
    health = service.healthcheck()
    assert models.allowed_models
    assert health["status"] == "ok"
    assert health["prompts"]["document_analysis_v1"] == "ok"
    assert health["prompts"]["rag_answer_v1"] == "ok"


def test_service_storage_error_is_warning(monkeypatch):
    monkeypatch.setattr(document_repository, "append_jsonl", lambda *args, **kwargs: False)
    result = run(
        RegRadarAIService().run_full_analysis(
            FullAnalysisInput(text=TEXT, document_id="failed-storage")
        )
    )
    assert result.analysis_metadata.document_saved is False
    assert any("persistence warning" in item for item in result.analysis_metadata.warnings)


def test_service_preserves_fallback_metadata(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza_with_fallback")
    monkeypatch.setenv("POLZA_API_KEY", "test-key")
    monkeypatch.setenv("POLZA_MAX_RETRIES", "0")
    reset_config()

    def unavailable(self, request):
        raise LLMProviderUnavailableError("HTTP 503", provider="polza")

    monkeypatch.setattr(PolzaAIProvider, "complete", unavailable)
    result = run(
        RegRadarAIService().run_full_analysis(
            FullAnalysisInput(text=TEXT, request_id="fallback-request")
        )
    )
    assert result.analysis_metadata.fallback_used is True
    assert result.analysis_metadata.fallback_reason
    assert result.analysis_metadata.request_id == "fallback-request"
    assert len(result.analysis_metadata.llm_call_ids) >= 2
