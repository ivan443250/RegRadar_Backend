"""Pure mapping functions between RegRadar.Api and AI-service contracts."""

from __future__ import annotations

import json
from enum import IntEnum

from ...ai.schemas import (
    ClientProfileForAI,
    ClientRelevance,
    NotificationDraft,
    RegulatoryEventCard,
)
from .schemas import (
    BackendContractClientDto,
    MainBackendClientImpactPayload,
    MainBackendClientProfileDto,
    MainBackendNotificationPayload,
    MainBackendRegulatoryEventPayload,
)


# Temporary compatibility values. They must be confirmed against RegRadar.Api
# enums before the integration is promoted beyond dev/integration use.
class MainImpactLevel(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class MainEventStatus(IntEnum):
    DRAFT = 0
    NEEDS_REVIEW = 1
    APPROVED = 2
    REJECTED = 3


class MainNotificationChannel(IntEnum):
    MOCK = 0
    EMAIL = 1
    BANK_APP = 2
    WEBHOOK = 3


class MainNotificationStatus(IntEnum):
    DRAFT = 0
    SENT_MOCK = 1


IMPACT_LEVEL_VALUES = {
    "low": MainImpactLevel.LOW,
    "medium": MainImpactLevel.MEDIUM,
    "high": MainImpactLevel.HIGH,
    "critical": MainImpactLevel.CRITICAL,
}
EVENT_STATUS_VALUES = {
    "draft": MainEventStatus.DRAFT,
    "needs_review": MainEventStatus.NEEDS_REVIEW,
    "approved": MainEventStatus.APPROVED,
    "rejected": MainEventStatus.REJECTED,
}
NOTIFICATION_CHANNEL_VALUES = {
    "mock": MainNotificationChannel.MOCK,
    "email_mock": MainNotificationChannel.EMAIL,
    "bank_app_mock": MainNotificationChannel.BANK_APP,
    "webhook_mock": MainNotificationChannel.WEBHOOK,
}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _level_is_active(value: int | str) -> bool:
    if isinstance(value, int):
        return value > 0
    return value.strip().casefold() not in {"", "none", "no", "low", "0"}


def map_main_client_profile_to_ai(
    dto: MainBackendClientProfileDto,
) -> ClientProfileForAI:
    tags: list[str] = [f"size:{dto.size}"]
    if dto.has_foreign_trade:
        tags.append("foreign_trade")
    if dto.uses_online_payments:
        tags.append("online_payments")
    if dto.handles_personal_data:
        tags.append("personal_data")
    if _level_is_active(dto.cash_operations_level):
        tags.append("cash_operations")
    if dto.bank_segment:
        tags.append(f"bank_segment:{dto.bank_segment}")
    if dto.industry:
        tags.append(f"industry:{dto.industry}")

    return ClientProfileForAI(
        client_id=dto.id,
        company_name=dto.company_name,
        okved=dto.okved,
        industry=dto.industry,
        size=str(dto.size),
        has_foreign_trade=dto.has_foreign_trade,
        uses_online_payments=dto.uses_online_payments,
        handles_personal_data=dto.handles_personal_data,
        cash_operations_level=str(dto.cash_operations_level),
        risk_profile=str(dto.risk_profile),
        bank_segment=dto.bank_segment,
        tags=_unique(tags),
    )


def map_backend_contract_client_to_ai(
    dto: BackendContractClientDto,
) -> ClientProfileForAI:
    tags: list[str] = []
    if dto.has_foreign_trade:
        tags.append("foreign_trade")
    if dto.uses_online_payments:
        tags.append("online_payments")
    if dto.handles_personal_data:
        tags.append("personal_data")
    if dto.cash_operations_level and dto.cash_operations_level.casefold() not in {
        "none",
        "no",
        "low",
        "0",
    }:
        tags.append("cash_operations")
    if dto.bank_segment:
        tags.append(f"bank_segment:{dto.bank_segment}")
    if dto.industry:
        tags.append(f"industry:{dto.industry}")
    return ClientProfileForAI(
        client_id=dto.client_id,
        company_name=dto.company_name,
        okved=dto.okved,
        industry=dto.industry,
        size=dto.size,
        has_foreign_trade=dto.has_foreign_trade,
        uses_online_payments=dto.uses_online_payments,
        handles_personal_data=dto.handles_personal_data,
        cash_operations_level=dto.cash_operations_level,
        risk_profile=dto.risk_profile,
        bank_segment=dto.bank_segment,
        tags=_unique(tags),
    )


def map_ai_event_card_to_main_payload(
    event_card: RegulatoryEventCard,
    document_id: str,
) -> MainBackendRegulatoryEventPayload:
    analysis = event_card.document_analysis
    tags = _unique(([analysis.domain] if analysis.domain else []) + analysis.topics)
    effective_date = analysis.key_dates[0] if analysis.key_dates else None
    return MainBackendRegulatoryEventPayload(
        document_id=document_id,
        title=event_card.title,
        summary=event_card.short_summary or analysis.short_summary,
        impact_level=int(IMPACT_LEVEL_VALUES[event_card.impact_level]),
        impact_explanation=event_card.impact_assessment.reasoning,
        effective_date=effective_date,
        status=int(EVENT_STATUS_VALUES[event_card.review_state]),
        tags=tags,
    )


def map_ai_client_relevance_to_main_impacts(
    client_relevance: list[ClientRelevance],
    regulatory_event_id: str | None = None,
) -> list[MainBackendClientImpactPayload]:
    result: list[MainBackendClientImpactPayload] = []
    for item in client_relevance:
        details = [item.explanation_for_bank, f"Relevance score: {item.relevance_score}/100."]
        if item.matched_factors:
            details.append(f"Matched factors: {', '.join(item.matched_factors)}.")
        if item.evidence_fragments:
            details.append(f"Evidence: {item.evidence_fragments[0]}")
        result.append(
            MainBackendClientImpactPayload(
                regulatory_event_id=regulatory_event_id,
                client_profile_id=item.client_id,
                company_name=item.client_name,
                impact_level=int(IMPACT_LEVEL_VALUES[item.relevance_level]),
                explanation=" ".join(details),
            )
        )
    return result


def map_notification_draft_to_main_payload(
    notification: NotificationDraft,
    regulatory_event_id: str | None = None,
    client_id: str | None = None,
    *,
    channel: str = "mock",
    sent_mock: bool = False,
) -> MainBackendNotificationPayload:
    return MainBackendNotificationPayload(
        regulatory_event_id=regulatory_event_id,
        client_profile_id=client_id or notification.client_id,
        payload=json.dumps(
            notification.model_dump(mode="json"),
            ensure_ascii=False,
        ),
        channel=int(NOTIFICATION_CHANNEL_VALUES.get(channel, MainNotificationChannel.MOCK)),
        status=int(
            MainNotificationStatus.SENT_MOCK
            if sent_mock
            else MainNotificationStatus.DRAFT
        ),
    )
