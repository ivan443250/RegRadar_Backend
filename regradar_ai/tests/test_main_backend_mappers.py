"""Contract tests for pure RegRadar.Api <-> AI DTO mapping."""

import json

from app.ai.event_card_service import create_event_card
from app.integrations.main_backend.mappers import (
    MainEventStatus,
    MainImpactLevel,
    MainNotificationChannel,
    MainNotificationStatus,
    map_ai_client_relevance_to_main_impacts,
    map_ai_event_card_to_main_payload,
    map_main_client_profile_to_ai,
    map_notification_draft_to_main_payload,
)
from app.integrations.main_backend.schemas import MainBackendClientProfileDto


TEXT = (
    "Организации обязаны соблюдать требования 152-ФЗ к обработке персональных "
    "данных и хранить согласия клиентов."
)


def main_profile(**overrides):
    data = {
        "id": "main-client-1",
        "companyName": "ООО Тест",
        "okved": "62.01",
        "industry": "it",
        "size": 2,
        "hasForeignTrade": True,
        "usesOnlinePayments": True,
        "handlesPersonalData": True,
        "cashOperationsLevel": 1,
        "riskProfile": 2,
        "bankSegment": "SME",
    }
    data.update(overrides)
    return MainBackendClientProfileDto.model_validate(data)


def test_main_client_profile_maps_to_ai_profile_and_tags():
    result = map_main_client_profile_to_ai(main_profile())
    assert result.client_id == "main-client-1"
    assert result.company_name == "ООО Тест"
    assert result.size == "2"
    assert result.cash_operations_level == "1"
    assert {
        "foreign_trade",
        "online_payments",
        "personal_data",
        "cash_operations",
        "bank_segment:SME",
        "industry:it",
    } <= set(result.tags)


def test_main_client_profile_accepts_final_backend_string_enums():
    result = map_main_client_profile_to_ai(
        main_profile(
            size="Medium",
            cashOperationsLevel="High",
            riskProfile="High",
        )
    )
    assert result.size == "Medium"
    assert result.cash_operations_level == "High"
    assert result.risk_profile == "High"
    assert "cash_operations" in result.tags


def test_ai_event_card_maps_to_main_regulatory_event_payload():
    card = create_event_card(TEXT)
    result = map_ai_event_card_to_main_payload(card, "document-1")
    assert result.document_id == "document-1"
    assert result.title == card.title
    assert result.summary == card.short_summary
    assert result.impact_level == int(MainImpactLevel.MEDIUM)
    assert result.status == int(MainEventStatus.NEEDS_REVIEW)
    assert "personal_data" in result.tags


def test_client_relevance_maps_to_main_impacts():
    card = create_event_card(TEXT)
    result = map_ai_client_relevance_to_main_impacts(
        card.client_relevance,
        regulatory_event_id="event-1",
    )
    assert result
    assert result[0].regulatory_event_id == "event-1"
    assert result[0].client_profile_id == card.client_relevance[0].client_id
    assert "Relevance score:" in result[0].explanation
    assert result[0].impact_level in {
        int(MainImpactLevel.LOW),
        int(MainImpactLevel.MEDIUM),
        int(MainImpactLevel.HIGH),
    }


def test_notification_draft_maps_to_json_payload():
    card = create_event_card(TEXT)
    draft = card.notification_drafts[0]
    result = map_notification_draft_to_main_payload(
        draft,
        regulatory_event_id="event-1",
    )
    payload = json.loads(result.payload)
    assert result.regulatory_event_id == "event-1"
    assert result.client_profile_id == draft.client_id
    assert result.channel == int(MainNotificationChannel.MOCK)
    assert result.status == int(MainNotificationStatus.DRAFT)
    assert payload["title"] == draft.title
    assert payload["disclaimer"]


def test_integration_dto_serializes_as_main_backend_camel_case():
    payload = main_profile().model_dump(mode="json", by_alias=True)
    assert payload["companyName"] == "ООО Тест"
    assert payload["hasForeignTrade"] is True
    assert "company_name" not in payload
