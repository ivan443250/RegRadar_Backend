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
    BackendContractImpact,
    BackendContractKeyDate,
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
                relevance_score=item.relevance_score,
                relevance_level=item.relevance_level,
                matched_factors=item.matched_factors,
                explanation_for_bank=item.explanation_for_bank,
                explanation_for_client=item.explanation_for_client,
                evidence_fragments=item.evidence_fragments,
            )
            for item in card.client_relevance
            if item.client_id in allowed_client_ids
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
                regulator=analysis.regulator,
                document_type=analysis.document_type,
                topics=analysis.topics,
                affected_industries=analysis.affected_industries,
                key_dates=_map_key_dates(analysis.key_dates, source_text) or None,
                obligations=analysis.obligations,
                source_fragments=analysis.source_fragments,
                confidence=analysis.confidence,
            ),
            impact=BackendContractImpact(
                impact_score=impact.impact_score,
                impact_level=impact.impact_level,
                reasoning=impact.reasoning,
                evidence_fragments=impact.evidence_fragments,
                urgency=impact.urgency,
                confidence=impact.confidence,
            ),
            client_relevances=relevances,
        )


def _request_chunks(
    request: BackendContractAnalyzeRequest,
) -> list[DocumentChunkForAI]:
    provided = [value.strip() for value in request.chunks if value.strip()]
    if provided:
        return [
            DocumentChunkForAI(
                chunk_id=f"chunk_{index}",
                text=text,
                order_index=index,
            )
            for index, text in enumerate(provided)
        ]
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
