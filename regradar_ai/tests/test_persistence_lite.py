"""JSONL repository contracts and upload/card persistence integration."""

import json

import pytest

from app.storage import (
    document_repository,
    event_repository,
    rag_chat_repository,
)
from app.storage.jsonl_repository import (
    append_jsonl,
    clear_jsonl_for_tests,
    read_jsonl,
    read_jsonl_reverse,
)


SAMPLE_TEXT = (
    "Организации обязаны соблюдать требования к обработке персональных данных "
    "и хранить согласия клиентов."
)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    paths = {
        "documents": tmp_path / "documents.jsonl",
        "chunks": tmp_path / "chunks.jsonl",
        "events": tmp_path / "events.jsonl",
        "rag_chats": tmp_path / "rag_chats.jsonl",
    }
    monkeypatch.setattr(document_repository, "DOCUMENTS_PATH", paths["documents"])
    monkeypatch.setattr(document_repository, "CHUNKS_PATH", paths["chunks"])
    monkeypatch.setattr(event_repository, "EVENTS_PATH", paths["events"])
    monkeypatch.setattr(rag_chat_repository, "RAG_CHATS_PATH", paths["rag_chats"])
    yield paths


def test_jsonl_primitives_append_read_reverse_and_clear(tmp_path):
    path = tmp_path / "nested" / "records.jsonl"
    assert append_jsonl(path, {"id": 1, "title": "Документ"}) is True
    assert append_jsonl(path, {"id": 2}) is True
    assert read_jsonl(path) == [
        {"id": 1, "title": "Документ"},
        {"id": 2},
    ]
    assert read_jsonl_reverse(path, 1) == [{"id": 2}]
    clear_jsonl_for_tests(path)
    assert read_jsonl(path) == []


def test_document_repository_does_not_store_full_text(isolated_storage):
    record = document_repository.DocumentRecord(
        document_id="doc-1",
        version_id="v1",
        filename="rule.txt",
        text_hash=document_repository.text_hash(SAMPLE_TEXT),
        extracted_text_length=len(SAMPLE_TEXT),
        chunks_count=1,
        metadata={"document_text": SAMPLE_TEXT, "source": "test"},
    )
    assert document_repository.save_document(record) is True
    stored = isolated_storage["documents"].read_text(encoding="utf-8")
    assert SAMPLE_TEXT not in stored
    assert "document_text" not in stored
    assert document_repository.get_document("doc-1") is not None
    assert document_repository.list_documents()[0].document_id == "doc-1"


def test_document_repository_saves_and_deduplicates_chunks(isolated_storage):
    chunk = document_repository.ChunkRecord(
        document_id="doc-1",
        version_id="v1",
        chunk_id="chunk_1",
        order=0,
        text=SAMPLE_TEXT,
        text_hash=document_repository.text_hash(SAMPLE_TEXT),
    )
    assert document_repository.save_chunks("doc-1", "v1", [chunk]) == 1
    assert document_repository.save_chunks("doc-1", "v1", [chunk]) == 1
    assert len(isolated_storage["chunks"].read_text(encoding="utf-8").splitlines()) == 1
    chunks = document_repository.get_chunks("doc-1", "v1")
    assert len(chunks) == 1
    assert chunks[0].text == SAMPLE_TEXT


def test_event_repository_saves_and_finds_latest_event(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("rule.txt", SAMPLE_TEXT.encode("utf-8"), "text/plain")},
        data={"document_id": "event-doc", "version_id": "v1"},
    )
    assert response.status_code == 200
    latest = event_repository.get_latest_event_by_document("event-doc", "v1")
    assert latest is not None
    assert latest["event_card"]["event_id"] == response.json()["card"]["event_card"]["event_id"]
    assert event_repository.get_event_card(latest["event_id"])["title"]


def test_rag_chat_repository_history():
    record = rag_chat_repository.RagChatRecord(
        chat_id="chat-1",
        message_id="message-1",
        document_id="doc-1",
        question="Какой срок?",
        answer="До 1 июля.",
        audience="bank_employee",
        no_data=False,
        source_chunk_ids=["chunk_1"],
    )
    assert rag_chat_repository.save_rag_exchange(record) is True
    history = rag_chat_repository.list_rag_history("doc-1")
    assert history[0]["question"] == "Какой срок?"
    assert rag_chat_repository.get_recent_rag_chats()[0]["chat_id"] == "chat-1"


def test_upload_create_card_persists_document_chunks_and_event(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("rule.txt", SAMPLE_TEXT.encode("utf-8"), "text/plain")},
        data={"document_id": "upload-doc", "version_id": "v1"},
    )
    data = response.json()
    metadata = data["card"]["event_card"]["analysis_metadata"]
    assert response.status_code == 200
    assert document_repository.get_document("upload-doc") is not None
    assert document_repository.get_chunks("upload-doc")
    assert event_repository.get_latest_event_by_document("upload-doc") is not None
    assert metadata["document_saved"] is True
    assert metadata["chunks_saved"] > 0
    assert metadata["event_saved"] is True
    assert metadata["storage_source"] == "jsonl"


def test_storage_write_error_does_not_break_upload(client, monkeypatch):
    monkeypatch.setattr(document_repository, "append_jsonl", lambda *args, **kwargs: False)
    monkeypatch.setattr(event_repository, "append_jsonl", lambda *args, **kwargs: False)
    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("rule.txt", SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    metadata = response.json()["card"]["event_card"]["analysis_metadata"]
    assert response.status_code == 200
    assert metadata["document_saved"] is False
    assert metadata["event_saved"] is False
    assert any("persistence warning" in warning for warning in metadata["warnings"])


def test_storage_debug_endpoints_do_not_return_full_document(client):
    client.post(
        "/api/documents/upload-analysis",
        files={"file": ("rule.txt", SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    documents = client.get("/api/debug/documents?limit=10")
    assert documents.status_code == 200
    assert SAMPLE_TEXT not in documents.text
    document_id = documents.json()[0]["document_id"]
    chunks = client.get(f"/api/debug/documents/{document_id}/chunks")
    assert chunks.status_code == 200
    assert chunks.json()[0]["text"]
    assert client.get("/api/debug/events?limit=201").status_code == 422


def test_runtime_directories_are_configurable(monkeypatch, tmp_path):
    from app.storage.paths import log_dir, storage_dir

    custom_storage = tmp_path / "runtime-storage"
    custom_logs = tmp_path / "runtime-logs"
    monkeypatch.setenv("REG_RADAR_STORAGE_DIR", str(custom_storage))
    monkeypatch.setenv("REG_RADAR_LOG_DIR", str(custom_logs))
    assert storage_dir() == custom_storage
    assert log_dir() == custom_logs
