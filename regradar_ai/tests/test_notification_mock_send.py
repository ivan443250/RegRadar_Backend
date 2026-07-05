"""End-to-end tests for safe mock-only notification delivery."""

import pytest

from app.storage import (
    document_repository,
    event_repository,
    notification_repository,
    rag_chat_repository,
)


PERSONAL_DATA_TEXT = (
    "Организации обязаны соблюдать требования 152-ФЗ к обработке персональных "
    "данных клиентов и хранить согласия пользователей."
)
NEUTRAL_TEXT = "Общие положения о развитии городской навигации и благоустройства."


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(document_repository, "DOCUMENTS_PATH", tmp_path / "documents.jsonl")
    monkeypatch.setattr(document_repository, "CHUNKS_PATH", tmp_path / "chunks.jsonl")
    monkeypatch.setattr(event_repository, "EVENTS_PATH", tmp_path / "events.jsonl")
    monkeypatch.setattr(notification_repository, "NOTIFICATIONS_PATH", tmp_path / "notifications.jsonl")
    monkeypatch.setattr(rag_chat_repository, "RAG_CHATS_PATH", tmp_path / "rag_chats.jsonl")


def _analysis(client, text=PERSONAL_DATA_TEXT):
    response = client.post("/api/ai/full-analysis", json={"text": text})
    assert response.status_code == 200
    return response.json()


def _send_payload(analysis, disclaimer=None):
    draft = dict(analysis["notification_drafts"][0])
    if disclaimer is not None:
        draft["disclaimer"] = disclaimer
    metadata = analysis["analysis_metadata"]
    return {
        "document_id": metadata["context_document_id"],
        "version_id": metadata["context_version_id"],
        "client_id": draft["client_id"],
        "client_name": draft["client_name"],
        "notification_id": draft["notification_id"],
        "notification": draft,
        "source_chunk_ids": draft["source_chunk_ids"],
    }


def test_mock_send_returns_sent_and_persists_delivery(client):
    analysis = _analysis(client)
    response = client.post(
        "/api/notifications/mock-send",
        json=_send_payload(analysis),
    )
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "sent_mock"
    assert data["delivery_id"]
    assert data["saved"] is True
    assert notification_repository.get_delivery(data["delivery_id"])["status"] == "sent_mock"


def test_empty_disclaimer_gets_safe_default(client):
    response = client.post(
        "/api/notifications/mock-send",
        json=_send_payload(_analysis(client), disclaimer=""),
    )
    assert response.status_code == 200
    assert "не является юридической консультацией" in response.json()["disclaimer"]


def test_storage_error_returns_saved_false(client, monkeypatch):
    analysis = _analysis(client)
    monkeypatch.setattr(notification_repository, "append_jsonl", lambda *args, **kwargs: False)
    response = client.post(
        "/api/notifications/mock-send",
        json=_send_payload(analysis),
    )
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "sent_mock"
    assert data["saved"] is False
    assert data["metadata"]["warnings"]


def test_neutral_document_send_is_blocked(client):
    analysis = _analysis(client, NEUTRAL_TEXT)
    metadata = analysis["analysis_metadata"]
    fake_draft = {
        "client_id": "seed-1",
        "client_name": "Demo",
        "title": "Уведомление",
        "short_message": "Может быть релевантно.",
        "full_message": "Рекомендуется проверить применимость.",
        "client_friendly_explanation": "Проверка.",
        "disclaimer": "Информационное уведомление.",
        "priority": "low",
    }
    response = client.post(
        "/api/notifications/mock-send",
        json={
            "document_id": metadata["context_document_id"],
            "client_id": "seed-1",
            "notification": fake_draft,
        },
    )
    assert response.status_code == 400
    assert "neutral_no_match" in response.text


def test_irrelevant_or_missing_client_is_not_sent(client):
    analysis = _analysis(client)
    payload = _send_payload(analysis)
    payload["client_id"] = "irrelevant-client"
    payload["notification"]["client_id"] = "irrelevant-client"
    assert client.post("/api/notifications/mock-send", json=payload).status_code == 400
    payload["client_id"] = ""
    assert client.post("/api/notifications/mock-send", json=payload).status_code == 422


def test_notification_debug_endpoints(client):
    analysis = _analysis(client)
    sent = client.post(
        "/api/notifications/mock-send",
        json=_send_payload(analysis),
    ).json()
    document_id = sent["document_id"]
    client_id = sent["client_id"]
    assert client.get("/api/debug/notifications?limit=10").json()
    assert client.get(f"/api/debug/notifications/by-document/{document_id}").json()
    assert client.get(f"/api/debug/notifications/by-client/{client_id}").json()
    assert client.get("/api/debug/notifications?limit=201").status_code == 422

