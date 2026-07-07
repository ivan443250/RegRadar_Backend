"""Minimal production contract used by the main .NET backend container."""

from __future__ import annotations

import re
from datetime import date

from ...ai.reg_radar_ai_service import RegRadarAIService
from ...ai.schemas import (
    CreateEventCardFromDocumentRequest,
    DocumentChunkForAI,
    DocumentMetadataForAI,
)
from ...services.document_chunker import chunk_text_for_document
from .mappers import map_backend_contract_client_to_ai
from .schemas import (
    BackendContractAnalyzeRequest,
    BackendContractAnalyzeResponse,
    BackendContractClientRelevance,
    BackendContractDocumentAnalysis,
    BackendContractEvidenceFragment,
    BackendContractImpact,
    BackendContractKeyDate,
    BackendContractMetadata,
    BackendContractNotificationDraft,
    BackendContractReview,
)


class BackendContractError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class BackendContractService:
    def __init__(self, ai_service: RegRadarAIService) -> None:
        self.ai_service = ai_service

    async def analyze(
        self,
        request: BackendContractAnalyzeRequest,
    ) -> BackendContractAnalyzeResponse:
        if not request.text.strip():
            raise BackendContractError("text must not be empty")

        chunks = _request_chunks(request)
        clients = [map_backend_contract_client_to_ai(item) for item in request.clients]
        result = await self.ai_service.create_event_card_from_document(
            CreateEventCardFromDocumentRequest(
                document_id=request.document_id,
                version_id="v1",
                chunks=chunks,
                metadata=DocumentMetadataForAI(
                    title=request.title,
                    source="main_backend_contract",
                ),
                source_type="main_backend_contract",
                client_profiles=clients,
                use_seed_fallback=False,
            ),
            endpoint="/analyze",
        )
        card = result.event_card
        metadata = card.analysis_metadata
        allowed_client_ids = {item.client_id for item in clients}
        relevances = [
            BackendContractClientRelevance(
                client_id=item.client_id,
                client_name=item.client_name,
                relevance_score=item.relevance_score,
                relevance_level=item.relevance_level,
                matched_factors=item.matched_factors,
                explanation_for_bank=item.explanation_for_bank,
                explanation_for_client=item.explanation_for_client,
                evidence_fragments=item.evidence_fragments,
                recommended_notification_type=item.recommended_notification_type,
            )
            for item in card.client_relevance
            if item.client_id in allowed_client_ids
        ]
        drafts = [
            BackendContractNotificationDraft(
                notification_id=draft.notification_id,
                client_id=draft.client_id,
                client_name=draft.client_name,
                title=draft.title,
                short_message=draft.short_message,
                full_message=draft.full_message,
                client_friendly_explanation=draft.client_friendly_explanation,
                source_link=draft.source_link,
                disclaimer=draft.disclaimer,
                priority=draft.priority,
                channel_payload=draft.channel_payload,
                document_id=draft.document_id,
                version_id=draft.version_id,
                source_chunk_ids=draft.source_chunk_ids,
            )
            for draft in card.notification_drafts
            if draft.client_id in allowed_client_ids
        ]
        evidence = [
            BackendContractEvidenceFragment(
                fragment_id=fragment.fragment_id,
                text=fragment.text,
                source_type=fragment.source_type,
                document_id=fragment.document_id,
                version_id=fragment.version_id,
                chunk_id=fragment.chunk_id,
                source_url=fragment.source_url,
                evidence_role=fragment.evidence_role,
            )
            for fragment in card.evidence_fragments
        ]
        analysis = card.document_analysis
        impact = card.impact_assessment
        source_text = "\n\n".join(chunk.text for chunk in chunks)
        return BackendContractAnalyzeResponse(
            provider=metadata.analysis_provider,
            model=metadata.selected_model or metadata.model_version,
            prompt_version=metadata.prompt_version,
            analysis=BackendContractDocumentAnalysis(
                title=card.title,
                short_summary=analysis.short_summary,
                long_summary=analysis.long_summary,
                domain=analysis.domain,
                regulator=analysis.regulator,
                document_type=analysis.document_type,
                status=analysis.status,
                topics=analysis.topics,
                affected_industries=analysis.affected_industries,
                affected_processes=analysis.affected_processes,
                key_dates=_map_key_dates(analysis.key_dates, source_text) or None,
                obligations=analysis.obligations,
                restrictions=analysis.restrictions,
                penalties_or_consequences=analysis.penalties_or_consequences,
                source_fragments=analysis.source_fragments,
                confidence=analysis.confidence,
            ),
            impact=BackendContractImpact(
                impact_score=impact.impact_score,
                impact_level=impact.impact_level,
                bank_impact=impact.bank_impact,
                client_impact=impact.client_impact,
                affected_processes=impact.affected_processes,
                possible_consequences=impact.possible_consequences,
                reasoning=impact.reasoning,
                evidence_fragments=impact.evidence_fragments,
                urgency=impact.urgency,
                confidence=impact.confidence,
            ),
            client_relevances=relevances,
            metadata=BackendContractMetadata(
                runtime=metadata.runtime,
                fallback_used=metadata.fallback_used,
                fallback_reason=metadata.fallback_reason,
                processing_mode=metadata.processing_mode,
                client_profiles_source=metadata.client_profiles_source,
                warnings=metadata.warnings,
                selected_model=metadata.selected_model,
                request_id=metadata.request_id,
                llm_call_ids=metadata.llm_call_ids,
                latency_ms=metadata.latency_ms,
            ),
            review=BackendContractReview(
                state=card.review_state,
                required=card.review_required,
                no_data_reason=card.no_data_reason,
            ),
            evidence=evidence,
            notification_drafts=drafts,
        )


def _request_chunks(
    request: BackendContractAnalyzeRequest,
) -> list[DocumentChunkForAI]:
    provided: list[DocumentChunkForAI] = []
    for index, value in enumerate(request.chunks):
        if isinstance(value, str):
            text = value.strip()
            if not text:
                continue
            provided.append(
                DocumentChunkForAI(
                    chunk_id=f"chunk_{index}",
                    text=text,
                    order_index=index,
                )
            )
            continue
        text = value.content.strip()
        if not text:
            continue
        provided.append(
            DocumentChunkForAI(
                chunk_id=value.chunk_id or f"chunk_{index}",
                text=text,
                order_index=value.chunk_index,
                section_title=value.section_title,
                page_number=value.page_number,
            )
        )
    if provided:
        return provided
    return chunk_text_for_document(request.text)


_RUSSIAN_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


def _map_key_dates(
    values: list[str],
    source_text: str,
) -> list[BackendContractKeyDate]:
    result: list[BackendContractKeyDate] = []
    source_lower = source_text.casefold()
    for value in values:
        parsed = _parse_source_date(value)
        if parsed is None:
            continue
        iso_date, source_token = parsed
        position = source_lower.find(source_token.casefold())
        if position < 0:
            # Do not expose a date that cannot be grounded in supplied chunks.
            continue
        context = source_lower[max(0, position - 100): position + len(source_token) + 100]
        result.append(
            BackendContractKeyDate(
                date=iso_date,
                meaning=_date_meaning(context),
            )
        )
    return list({item.date: item for item in result}.values())


def _parse_source_date(value: str) -> tuple[str, str] | None:
    iso = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", value)
    if iso:
        return _validated_date(int(iso[1]), int(iso[2]), int(iso[3]), iso[0])

    dotted = re.search(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", value)
    if dotted:
        return _validated_date(
            int(dotted[3]),
            int(dotted[2]),
            int(dotted[1]),
            dotted[0],
        )

    russian = re.search(
        r"\b(\d{1,2})\s+"
        r"(января|февраля|марта|апреля|мая|июня|июля|августа|"
        r"сентября|октября|ноября|декабря)\s+(\d{4})\b",
        value.casefold(),
    )
    if russian:
        return _validated_date(
            int(russian[3]),
            _RUSSIAN_MONTHS[russian[2]],
            int(russian[1]),
            russian[0],
        )
    return None


def _validated_date(
    year: int,
    month: int,
    day: int,
    source_token: str,
) -> tuple[str, str] | None:
    try:
        return date(year, month, day).isoformat(), source_token
    except ValueError:
        return None


def _date_meaning(context: str) -> str:
    if "вступ" in context:
        return "вступление в силу"
    if "опублик" in context:
        return "дата публикации"
    if "не позднее" in context or "до " in context:
        return "срок исполнения"
    if "начиная" in context:
        return "начало применения"
    return "дата, указанная в документе"
