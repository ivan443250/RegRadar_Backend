"""Upload-to-RegulatoryEventCard integration tests."""

import json

from app.ai.schemas import UploadCreateCardResponse
from app.services.document_chunker import chunk_text_for_document
from app.services.document_text_extractor import MAX_FILE_SIZE_BYTES
from app.services.document_text_cleaner import (
    EVAL_METADATA_FIELDS,
    clean_eval_metadata,
)
from tests.test_upload_analysis import _minimal_pdf


SAMPLE_TEXT = (
    "Проект предусматривает новые требования к обработке персональных данных. "
    "Организации должны соблюдать положения 152-ФЗ и хранить согласия клиентов. "
    "За нарушение требований может наступать ответственность."
)

EVAL_ANNOTATED_TEXT = """DOCUMENT_TITLE: Тестовый заголовок
DOCUMENT_DATE: 2026-07-03
DOCUMENT_TYPE_EXPECTED: постановление
DOMAIN_EXPECTED: personal_data
SOURCE_FILE: source.txt
TOPICS_EXPECTED: personal_data
IMPACT_LEVEL_EXPECTED: medium
Постановление устанавливает требования к обработке персональных данных.
Организации должны хранить согласия клиентов.
"""

EVAL_CLEAN_TEXT = clean_eval_metadata(EVAL_ANNOTATED_TEXT)


def test_chunking_is_stable_ordered_and_non_empty():
    text = "Первое предложение. Второе предложение. Третье предложение."

    chunks = chunk_text_for_document(text, max_chars=25)

    assert [chunk.chunk_id for chunk in chunks] == ["chunk_1", "chunk_2", "chunk_3"]
    assert [chunk.order_index for chunk in chunks] == [0, 1, 2]
    assert all(chunk.text.strip() for chunk in chunks)
    assert " ".join(chunk.text for chunk in chunks) == text


def test_upload_create_card_txt_returns_typed_review_card(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("regulation.txt", SAMPLE_TEXT.encode(), "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    UploadCreateCardResponse.model_validate(data)
    assert data["filename"] == "regulation.txt"
    assert data["content_type"] == "text/plain"
    assert data["extracted_text_length"] == len(SAMPLE_TEXT)
    assert data["document_id"] == "upload_regulation"
    assert data["version_id"] == "v1"
    assert data["chunks_count"] >= 1

    card = data["card"]["event_card"]
    assert card["title"] == card["document_analysis"]["title"]
    assert card["title"] != "regulation.txt"
    assert card["impact_score"] >= 0
    assert card["impact_level"] in {"low", "medium", "high", "critical"}
    assert card["review_state"] == "needs_review"
    assert card["review_required"] is True
    assert card["analysis_metadata"]


def test_upload_create_card_cleans_eval_metadata_before_chunks_and_evidence(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={
            "file": (
                "annotated-real-sample.txt",
                EVAL_ANNOTATED_TEXT.encode("utf-8"),
                "text/plain",
            )
        },
        data={"document_id": "clean-eval-doc", "version_id": "eval-v1"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["extracted_text_length"] == len(EVAL_CLEAN_TEXT)

    card = data["card"]["event_card"]
    serialized_card = json.dumps(card, ensure_ascii=False)
    for field in EVAL_METADATA_FIELDS:
        assert f"{field}:" not in serialized_card

    assert card["document_analysis"]["short_summary"].startswith(
        "Постановление устанавливает требования"
    )
    assert card["evidence_fragments"]
    for evidence in card["evidence_fragments"]:
        assert evidence["text"] in EVAL_CLEAN_TEXT


def test_upload_create_card_evidence_links_to_document_version_and_chunks(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("evidence.txt", SAMPLE_TEXT.encode(), "text/plain")},
        data={"document_id": "doc-upload-42", "version_id": "ver-7"},
    )

    card = response.json()["card"]["event_card"]
    assert card["evidence_fragments"]
    for evidence in card["evidence_fragments"]:
        assert evidence["document_id"] == "doc-upload-42"
        assert evidence["version_id"] == "ver-7"
        assert evidence["chunk_id"].startswith("chunk_")


def test_upload_create_card_accepts_explicit_metadata(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("document.txt", SAMPLE_TEXT.encode(), "text/plain")},
        data={
            "document_id": "custom-doc",
            "version_id": "version-2026",
            "title": "Пользовательский заголовок",
            "source_url": "https://example.org/regulation",
        },
    )

    data = response.json()
    card = data["card"]["event_card"]
    assert data["document_id"] == "custom-doc"
    assert data["version_id"] == "version-2026"
    assert card["title"] == "Пользовательский заголовок"
    assert card["source_set"] == ["https://example.org/regulation"]


def test_upload_create_card_uses_filename_only_when_analysis_title_empty(
    client,
    monkeypatch,
):
    from app.ai import event_card_service
    from app.ai.service import full_ai_analysis

    analysis = full_ai_analysis(SAMPLE_TEXT)
    blank_document = analysis.document_analysis.model_copy(update={"title": ""})
    blank_title_analysis = analysis.model_copy(
        update={"document_analysis": blank_document}
    )
    monkeypatch.setattr(
        event_card_service,
        "full_ai_analysis",
        lambda _: blank_title_analysis,
    )

    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("fallback-name.txt", SAMPLE_TEXT.encode(), "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["card"]["event_card"]["title"] == "fallback-name.txt"


def test_upload_create_card_without_profiles_uses_seed_fallback(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("document.txt", SAMPLE_TEXT.encode(), "text/plain")},
    )

    card = response.json()["card"]["event_card"]
    assert card["analysis_metadata"]["client_profiles_source"] == "seed_fallback"
    assert any(item["client_id"].startswith("seed-") for item in card["client_relevance"])


def test_upload_create_card_custom_profiles_control_matching(client):
    profiles = [
        {
            "client_id": "upload-card-client",
            "company_name": "ООО Карточка Клиента",
            "handles_personal_data": True,
        }
    ]
    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("document.txt", SAMPLE_TEXT.encode(), "text/plain")},
        data={"client_profiles_json": json.dumps(profiles, ensure_ascii=False)},
    )

    assert response.status_code == 200
    card = response.json()["card"]["event_card"]
    assert card["analysis_metadata"]["client_profiles_source"] == "request"
    assert [item["client_id"] for item in card["client_relevance"]] == [
        "upload-card-client"
    ]
    assert [item["client_id"] for item in card["notification_drafts"]] == [
        "upload-card-client"
    ]


def test_upload_create_card_runs_analysis_once(client, monkeypatch):
    from app.ai import event_card_service

    original_analysis = event_card_service.full_ai_analysis
    calls: list[str] = []

    def tracked_analysis(text, client_profiles=None):
        calls.append(text)
        return original_analysis(text, client_profiles)

    monkeypatch.setattr(event_card_service, "full_ai_analysis", tracked_analysis)

    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("document.txt", SAMPLE_TEXT.encode(), "text/plain")},
    )

    assert response.status_code == 200
    assert calls == [SAMPLE_TEXT]


def test_upload_create_card_supports_pdf_text_layer(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={
            "file": (
                "regulation.pdf",
                _minimal_pdf("New regulation creates reporting obligations."),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "regulation.pdf"
    assert data["chunks_count"] == 1
    assert data["card"]["event_card"]["event_id"]


def test_upload_create_card_invalid_profiles_returns_422(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("document.txt", SAMPLE_TEXT.encode(), "text/plain")},
        data={"client_profiles_json": "{not-json"},
    )

    assert response.status_code == 422
    assert "client_profiles_json" in response.json()["detail"]


def test_upload_create_card_empty_txt_returns_422(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 422
    assert "empty" in response.json()["detail"].lower()


def test_upload_create_card_unsupported_extension_returns_400(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={"file": ("document.docx", b"not a docx", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "only .txt and .pdf" in response.json()["detail"].lower()


def test_upload_create_card_over_size_limit_returns_413(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={
            "file": (
                "large.txt",
                b"a" * (MAX_FILE_SIZE_BYTES + 1),
                "text/plain",
            )
        },
    )

    assert response.status_code == 413
    assert "10 mb" in response.json()["detail"].lower()


def test_upload_create_card_endpoint_is_present_in_openapi(client):
    schema = client.get("/openapi.json").json()
    assert "/api/documents/upload-create-card" in schema["paths"]
