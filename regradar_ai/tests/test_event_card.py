"""Smoke-тесты для цепочки создания RegulatoryEventCard.

Проверяют, что карточка корректно создаётся из текста и из document-контракта.
"""


import pytest

from app.ai import event_card_service
from app.ai.event_card_service import create_event_card, create_event_card_from_document_payload
from app.ai.service import full_ai_analysis
from app.ai.schemas import (
    CreateEventCardFromDocumentRequest,
    DocumentChunkForAI,
    DocumentMetadataForAI,
    RegulatoryEventCard,
)


SAMPLE_TEXT = (
    "Проект предусматривает новые требования к обработке персональных данных "
    "клиентов. Организации должны обеспечить хранение согласий пользователей "
    "и соблюдать положения 152-ФЗ. За нарушение требований может наступать "
    "ответственность."
)


# --- create_event_card ---


def test_create_event_card_returns_regulatory_event_card():
    card = create_event_card(SAMPLE_TEXT)
    assert isinstance(card, RegulatoryEventCard)


def test_create_event_card_has_event_id():
    card = create_event_card(SAMPLE_TEXT)
    assert card.event_id
    assert len(card.event_id) > 0


def test_create_event_card_has_impact():
    card = create_event_card(SAMPLE_TEXT)
    assert card.impact_score >= 0
    assert card.impact_level in {"low", "medium", "high", "critical"}


def test_create_event_card_has_evidence_fragments():
    card = create_event_card(SAMPLE_TEXT)
    assert isinstance(card.evidence_fragments, list)
    assert len(card.evidence_fragments) > 0, "Должны быть evidence_fragments для 152-ФЗ"
    fragment = card.evidence_fragments[0]
    assert fragment.text
    assert fragment.fragment_id
    assert fragment.evidence_role


def test_create_event_card_review_state_is_needs_review():
    card = create_event_card(SAMPLE_TEXT)
    assert card.review_state == "needs_review"


def test_create_event_card_has_nested_analysis():
    card = create_event_card(SAMPLE_TEXT)
    assert card.document_analysis.title
    assert card.impact_assessment.reasoning
    assert isinstance(card.client_relevance, list)
    assert isinstance(card.notification_drafts, list)


def test_create_event_card_review_required_for_high_impact():
    """При высоком impact_level review_required = True."""
    high_impact_text = (
        "Новые требования 152-ФЗ к обработке персональных данных и 115-ФЗ "
        "в сфере ПОД/ФТ. Организации должны обновить процедуры. "
        "За нарушение предусмотрены штрафы и ответственность."
    )
    card = create_event_card(high_impact_text)

    assert card.impact_level in {"high", "critical"}
    assert card.review_required is True


def test_create_event_card_review_required_for_low_confidence(monkeypatch):
    """При confidence < 0.75 review_required = True."""
    analysis = full_ai_analysis("Общие положения о развитии цифровых сервисов.")
    low_confidence_document = analysis.document_analysis.model_copy(
        update={"confidence": 0.70}
    )
    low_confidence_analysis = analysis.model_copy(
        update={"document_analysis": low_confidence_document}
    )
    monkeypatch.setattr(
        event_card_service,
        "full_ai_analysis",
        lambda _: low_confidence_analysis,
    )

    card = event_card_service.create_event_card(
        "Общие положения о развитии цифровых сервисов."
    )

    assert card.confidence == 0.70
    assert card.review_required is True


def test_create_event_card_model_version():
    card = create_event_card(SAMPLE_TEXT)
    assert card.model_version
    assert card.prompt_version
    assert card.created_by


# --- create_event_card_from_document_payload ---


def test_create_card_from_document_links_evidence_to_chunks():
    """Evidence привязывается к document_id, version_id и chunk_id."""
    payload = CreateEventCardFromDocumentRequest(
        document_id="doc-100",
        version_id="ver-100",
        chunks=[
            DocumentChunkForAI(
                chunk_id="chunk-1",
                text=SAMPLE_TEXT,
                order_index=1,
                section_title="Требования",
                page_number=1,
            ),
        ],
        metadata=DocumentMetadataForAI(
            title="Тестовый документ",
            source="demo",
            original_url="https://example.org/doc-100",
        ),
        source_type="uploaded_text",
    )
    response = create_event_card_from_document_payload(payload)
    card = response.event_card

    assert card.event_id
    assert card.title == "Тестовый документ"
    assert len(card.evidence_fragments) > 0
    for fragment in card.evidence_fragments:
        assert fragment.document_id == "doc-100"
        assert fragment.version_id == "ver-100"
        assert fragment.chunk_id == "chunk-1"


def test_create_card_from_document_source_set():
    """source_set использует original_url из metadata."""
    payload = CreateEventCardFromDocumentRequest(
        document_id="doc-200",
        version_id="ver-200",
        chunks=[
            DocumentChunkForAI(
                chunk_id="chunk-1",
                text=SAMPLE_TEXT,
                order_index=1,
            ),
        ],
        metadata=DocumentMetadataForAI(
            original_url="https://example.org/doc-200",
        ),
    )
    response = create_event_card_from_document_payload(payload)
    assert "https://example.org/doc-200" in response.event_card.source_set


def test_create_card_from_document_uses_request_client_profiles():
    """Document payload использует переданные профили вместо SEED_CLIENTS."""
    from app.ai.schemas import ClientProfileForAI

    payload = CreateEventCardFromDocumentRequest(
        document_id="doc-300",
        version_id="ver-300",
        chunks=[
            DocumentChunkForAI(
                chunk_id="chunk-1",
                text=SAMPLE_TEXT,
                order_index=1,
            ),
        ],
        metadata=DocumentMetadataForAI(),
        client_profiles=[
            ClientProfileForAI(
                client_id="custom-1",
                company_name="Моя Компания",
                handles_personal_data=True,
            ),
        ],
    )
    response = create_event_card_from_document_payload(payload)
    client_names = [c.client_name for c in response.event_card.client_relevance]
    notification_names = [
        item.client_name for item in response.event_card.notification_drafts
    ]
    assert client_names == ["Моя Компания"]
    assert notification_names == ["Моя Компания"]
