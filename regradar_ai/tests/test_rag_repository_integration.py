"""RAG-lite integration with persisted chunks and JSONL chat history."""

import pytest

from app.ai.rag_context_store import clear_document_contexts
from app.storage import (
    document_repository,
    event_repository,
    rag_chat_repository,
)


RAG_TEXT = "Банк обязан завершить проверку документов в срок до 1 июля."


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(document_repository, "DOCUMENTS_PATH", tmp_path / "documents.jsonl")
    monkeypatch.setattr(document_repository, "CHUNKS_PATH", tmp_path / "chunks.jsonl")
    monkeypatch.setattr(event_repository, "EVENTS_PATH", tmp_path / "events.jsonl")
    monkeypatch.setattr(rag_chat_repository, "RAG_CHATS_PATH", tmp_path / "rag_chats.jsonl")
    clear_document_contexts()
    yield
    clear_document_contexts()


def _upload(client):
    response = client.post(
        "/api/documents/upload-analysis",
        files={"file": ("bank-rule.txt", RAG_TEXT.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 200
    return response.json()["document_id"]


def test_rag_answers_by_document_id_from_repository(client):
    document_id = _upload(client)
    clear_document_contexts()
    response = client.post(
        "/api/rag/ask",
        json={
            "question": "Какой срок установлен для банка?",
            "document_id": document_id,
            "version_id": "v1",
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["no_data"] is False
    assert data["source_fragments"]
    assert data["metadata"]["rag_chat_saved"] is True
    history = rag_chat_repository.list_rag_history(document_id)
    assert history[0]["no_data"] is False
    assert history[0]["source_chunk_ids"]


def test_unknown_document_returns_no_data_and_saves_history(client):
    response = client.post(
        "/api/rag/ask",
        json={
            "question": "Какой срок?",
            "document_id": "unknown-document",
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["no_data"] is True
    assert data["source_fragments"] == []
    history = rag_chat_repository.list_rag_history("unknown-document")
    assert history[0]["no_data"] is True
    assert history[0]["answer"] == "Нет данных в базе по этому вопросу."


def test_rag_chat_debug_endpoint_filters_by_document(client):
    document_id = _upload(client)
    client.post(
        "/api/rag/ask",
        json={"question": "Какой срок?", "document_id": document_id},
    )
    response = client.get(
        f"/api/debug/rag-chats?document_id={document_id}&limit=20"
    )
    assert response.status_code == 200
    assert response.json()[0]["document_id"] == document_id
    assert client.get("/api/debug/rag-chats?limit=201").status_code == 422

