import re
import inspect
from uuid import uuid4

from .schemas import (
    CreateEventCardFromDocumentRequest,
    CreateEventCardFromDocumentResponse,
    ClientProfileForAI,
    EvidenceFragment,
    RegulatoryEventCard,
)
from .service import full_ai_analysis


NO_DATA_REASON = "Недостаточно фрагментов источника для уверенного вывода"


def _run_full_analysis(
    text: str,
    client_profiles: list[ClientProfileForAI] | None,
    model_override: str | None,
    request_id: str | None,
    endpoint: str | None,
    use_seed_fallback: bool,
):
    """Preserve lightweight monkeypatch adapters used by existing tests."""
    parameters = inspect.signature(full_ai_analysis).parameters
    args = [text]
    if client_profiles is not None or model_override is not None:
        args.append(client_profiles)
    if model_override is not None:
        args.append(model_override)
    kwargs = {}
    if "request_id" in parameters:
        kwargs["request_id"] = request_id
    if "endpoint" in parameters:
        kwargs["endpoint"] = endpoint
    if "use_seed_fallback" in parameters:
        kwargs["use_seed_fallback"] = use_seed_fallback
    return full_ai_analysis(*args, **kwargs)


def create_event_card(
    text: str,
    source_type: str = "uploaded_text",
    source_url: str | None = None,
    client_profiles: list[ClientProfileForAI] | None = None,
    model_override: str | None = None,
    request_id: str | None = None,
    endpoint: str | None = None,
    use_seed_fallback: bool = True,
) -> RegulatoryEventCard:
    """Собрать единую карточку регуляторного события из mock AI-анализа."""
    analysis = _run_full_analysis(
        text,
        client_profiles,
        model_override,
        request_id,
        endpoint,
        use_seed_fallback,
    )
    document = analysis.document_analysis
    impact = analysis.impact_assessment
    event_id = str(uuid4())
    evidence_fragments: list[EvidenceFragment] = []
    seen_evidence: set[str] = set()

    def add_evidence(fragments: list[str], evidence_role: str) -> None:
        for fragment in fragments:
            if not fragment.strip():
                continue
            normalized = (
                re.sub(r"\s+", " ", fragment)
                .strip()
                .rstrip(".!?")
                .casefold()
            )
            if normalized in seen_evidence:
                continue
            seen_evidence.add(normalized)
            evidence_fragments.append(
                EvidenceFragment(
                    fragment_id=f"{event_id}-evidence-{len(evidence_fragments) + 1}",
                    text=fragment,
                    source_type=source_type,
                    source_url=source_url,
                    evidence_role=evidence_role,
                )
            )

    add_evidence(document.source_fragments, "document_source")
    add_evidence(impact.evidence_fragments, "impact_assessment")
    for client in analysis.client_relevance:
        add_evidence(client.evidence_fragments, "client_relevance")

    confidence = min(document.confidence, impact.confidence)
    review_required = True

    return RegulatoryEventCard(
        event_id=event_id,
        title=document.title,
        short_summary=document.short_summary,
        current_status="обнаружено",
        review_state="needs_review",
        topics=document.topics,
        affected_industries=document.affected_industries,
        affected_processes=impact.affected_processes,
        impact_score=impact.impact_score,
        impact_level=impact.impact_level,
        urgency=impact.urgency,
        confidence=confidence,
        evidence_fragments=evidence_fragments,
        source_set=[source_url] if source_url else ["uploaded_text"],
        model_version=analysis.analysis_metadata.model_version,
        prompt_version=analysis.analysis_metadata.prompt_version,
        created_by=analysis.analysis_metadata.analysis_provider,
        review_required=review_required,
        no_data_reason=None if evidence_fragments else NO_DATA_REASON,
        document_analysis=document,
        impact_assessment=impact,
        client_relevance=analysis.client_relevance,
        notification_drafts=analysis.notification_drafts,
        analysis_metadata=analysis.analysis_metadata,
    )


def create_event_card_from_document_payload(
    payload: CreateEventCardFromDocumentRequest,
    request_id: str | None = None,
    endpoint: str | None = None,
) -> CreateEventCardFromDocumentResponse:
    """Создать карточку из будущего backend-контракта без персистентности."""
    sorted_chunks = sorted(payload.chunks, key=lambda chunk: chunk.order_index)
    text = "\n\n".join(chunk.text for chunk in sorted_chunks)
    effective_source_url = payload.source_url or payload.metadata.original_url

    event_card = create_event_card(
        text=text,
        source_type=payload.source_type,
        source_url=effective_source_url,
        client_profiles=payload.client_profiles,
        model_override=payload.model_override,
        request_id=request_id or payload.request_id,
        endpoint=endpoint,
        use_seed_fallback=payload.use_seed_fallback,
    )

    if payload.metadata.title and payload.metadata.title.strip():
        event_card.title = payload.metadata.title.strip()

    has_unlinked_evidence = not event_card.evidence_fragments
    for evidence in event_card.evidence_fragments:
        matching_chunk = next(
            (chunk for chunk in sorted_chunks if evidence.text in chunk.text),
            None,
        )
        evidence.document_id = payload.document_id
        evidence.version_id = payload.version_id
        evidence.chunk_id = matching_chunk.chunk_id if matching_chunk else None
        evidence.source_url = effective_source_url
        evidence.source_type = payload.source_type
        if matching_chunk is None:
            has_unlinked_evidence = True

    event_card.source_set = [
        effective_source_url or payload.source_type
    ]
    if has_unlinked_evidence:
        event_card.review_required = True

    return CreateEventCardFromDocumentResponse(event_card=event_card)
