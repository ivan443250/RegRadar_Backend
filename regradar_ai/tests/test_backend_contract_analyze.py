"""Final /analyze contract used by the main .NET backend."""

import pytest

from app.ai.gateway.config import reset_config
from app.ai.llm_call_logger import clear_llm_call_logs_for_tests
from app.ai.service_factory import reset_reg_radar_ai_service_for_tests
from app.storage import (
    document_repository,
    event_repository,
    notification_repository,
    rag_chat_repository,
)


CLIENT = {
    "clientId": "client-guid-42",
    "companyName": "ООО Персональные сервисы",
    "okved": "62.01",
    "industry": "IT",
    "size": "Medium",
    "hasForeignTrade": False,
    "usesOnlinePayments": True,
    "handlesPersonalData": True,
    "cashOperationsLevel": "Low",
    "riskProfile": "High",
    "bankSegment": "Средний бизнес",
}


def payload(*, clients=None, text=None, chunks=None):
    return {
        "documentId": "document-guid-1",
        "title": "Требования к персональным данным",
        "text": text
        if text is not None
        else "Организации обрабатывают данные клиентов.",
        "chunks": chunks
        if chunks is not None
        else [
            "Организации обязаны соблюдать требования 152-ФЗ к обработке "
            "персональных данных и хранить согласия клиентов."
        ],
        "clients": [CLIENT] if clients is None else clients,
    }


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
    clear_llm_call_logs_for_tests()
    yield
    reset_config()
    reset_reg_radar_ai_service_for_tests()
    clear_llm_call_logs_for_tests()


def test_analyze_happy_path_contract_and_ready_chunks(client):
    response = client.post("/analyze", json=payload())
    data = response.json()
    assert response.status_code == 200
    assert set(data) == {
        "provider",
        "model",
        "promptVersion",
        "analysis",
        "impact",
        "clientRelevances",
        "metadata",
        "review",
        "evidence",
        "notificationDrafts",
    }
    assert data["provider"] == "mock"
    assert data["model"]
    assert data["promptVersion"] == "document_analysis_v1"
    assert "персональные данные" in data["analysis"]["topics"]
    assert data["analysis"]["title"] == "Требования к персональным данным"
    assert data["impact"]["impact_score"] >= 0
    assert data["metadata"]["runtime"] == "MOCK"
    assert data["review"]["state"] in {"draft", "needs_review", "approved", "rejected"}
    assert isinstance(data["review"]["required"], bool)
    assert isinstance(data["evidence"], list)
    assert isinstance(data["notificationDrafts"], list)


def test_analyze_returns_extended_analysis_impact_and_relevance_fields(client):
    response = client.post("/analyze", json=payload())
    data = response.json()
    assert response.status_code == 200
    analysis = data["analysis"]
    for field in (
        "domain",
        "status",
        "affected_processes",
        "restrictions",
        "penalties_or_consequences",
    ):
        assert field in analysis
    impact = data["impact"]
    for field in (
        "bank_impact",
        "client_impact",
        "affected_processes",
        "possible_consequences",
    ):
        assert field in impact
    relevance = data["clientRelevances"][0]
    assert relevance["client_name"] == "ООО Персональные сервисы"
    assert relevance["recommended_notification_type"]
    drafts = data["notificationDrafts"]
    assert drafts
    assert {item["clientId"] for item in drafts} == {"client-guid-42"}
    assert all(item["disclaimer"] for item in drafts)


def test_analyze_accepts_structured_chunks_with_real_ids(client):
    structured = [
        {
            "chunkId": "backend-chunk-guid-1",
            "chunkIndex": 0,
            "content": (
                "Организации обязаны соблюдать требования 152-ФЗ к обработке "
                "персональных данных и хранить согласия клиентов."
            ),
            "pageNumber": 3,
            "sectionTitle": "Статья 2",
        }
    ]
    response = client.post("/analyze", json=payload(chunks=structured))
    data = response.json()
    assert response.status_code == 200
    assert "персональные данные" in data["analysis"]["topics"]
    chunk_ids = {
        item["chunkId"]
        for item in data["evidence"]
        if item["chunkId"] is not None
    }
    assert chunk_ids <= {"backend-chunk-guid-1"}


def test_response_client_id_is_strictly_copied_from_request(client):
    response = client.post("/analyze", json=payload())
    relevances = response.json()["clientRelevances"]
    assert response.status_code == 200
    assert relevances
    assert {item["client_id"] for item in relevances} == {"client-guid-42"}


def test_empty_clients_returns_empty_relevances_without_seed(client):
    response = client.post("/analyze", json=payload(clients=[]))
    assert response.status_code == 200
    assert response.json()["clientRelevances"] == []


def test_empty_text_returns_contract_error(client):
    response = client.post("/analyze", json=payload(text=""))
    assert response.status_code == 400
    assert set(response.json()) == {"error"}
    assert "text must not be empty" in response.json()["error"]


def test_invalid_request_uses_contract_error_shape(client):
    response = client.post("/analyze", json={"text": "document"})
    assert response.status_code == 400
    assert set(response.json()) == {"error"}


def test_levels_are_limited_to_backend_contract(client):
    response = client.post("/analyze", json=payload())
    data = response.json()
    allowed = {"low", "medium", "high", "critical"}
    assert data["impact"]["impact_level"] in allowed
    assert all(item["relevance_level"] in allowed for item in data["clientRelevances"])


def test_dates_are_not_invented_when_sources_have_no_dates(client):
    response = client.post("/analyze", json=payload())
    assert response.status_code == 200
    assert response.json()["analysis"]["key_dates"] is None


def test_explicit_key_date_is_grounded_and_normalized(client):
    dated_text = "Документ вступает в силу 1 октября 2026 года."
    response = client.post(
        "/analyze",
        json=payload(text=dated_text, chunks=[dated_text]),
    )
    assert response.status_code == 200
    assert response.json()["analysis"]["key_dates"] == [
        {"date": "2026-10-01", "meaning": "вступление в силу"}
    ]


def test_existing_extended_integration_endpoint_remains_available(client):
    response = client.post(
        "/api/integration/main-backend/analyze-document",
        json={
            "document": {
                "id": "extended-doc",
                "title": "Документ",
                "text": "Требования 152-ФЗ к обработке персональных данных.",
            },
            "clientProfiles": [
                {
                    "id": "extended-client",
                    "companyName": "ООО Клиент",
                    "size": 1,
                    "hasForeignTrade": False,
                    "usesOnlinePayments": False,
                    "handlesPersonalData": True,
                    "cashOperationsLevel": 0,
                    "riskProfile": 1,
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["documentId"] == "extended-doc"
