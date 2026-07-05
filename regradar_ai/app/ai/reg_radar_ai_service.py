"""Stable backend-facing facade for the RegRadar AI module."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from pydantic import BaseModel, Field

from ..services.document_chunker import chunk_text_for_document
from ..storage import (
    document_repository,
    event_repository,
    notification_repository,
    rag_chat_repository,
)
from ..storage.persistence_service import (
    apply_persistence_metadata,
    persist_document,
    persist_event,
)
from .document_analysis_service import analyze_document_with_safe_fallback
from .event_card_service import create_event_card_from_document_payload
from .gateway.config import GatewayConfig, get_config
from .model_catalog import public_model_catalog
from .notification_safety import (
    ensure_notification_disclaimer,
    validate_notification_can_be_sent,
)
from .prompt_loader import PROMPTS_DIR
from .rag_context_store import context_fragments_from_sources, save_document_context
from .rag_service import ask_rag
from .schemas import (
    AIModelsResponse,
    ClientProfileForAI,
    ClientRelevance,
    CreateEventCardFromDocumentRequest,
    CreateEventCardFromDocumentResponse,
    DocumentAnalysis,
    DocumentChunkForAI,
    DocumentMetadataForAI,
    FullAIAnalysisResponse,
    NotificationDraft,
    NotificationMockChannel,
    NotificationMockSendRequest,
    NotificationMockSendResponse,
    RagAnswer,
    RagAskRequest,
    RagAudience,
    RagFragmentInput,
    RegulatoryEventCard,
)
from .service import full_ai_analysis


class AnalyzeDocumentInput(BaseModel):
    text: str = Field(min_length=1)
    document_id: str | None = None
    version_id: str = "v1"
    title: str | None = None
    source_url: str | None = None
    model_override: str | None = None
    request_id: str | None = None


class FullAnalysisInput(AnalyzeDocumentInput):
    client_profiles: list[ClientProfileForAI] | None = None
    filename: str | None = None
    content_type: str | None = None
    source: str = "full_analysis"
    use_seed_fallback: bool = True


class CreateEventCardInput(FullAnalysisInput):
    source_type: str = "uploaded_text"


class RagAskInput(BaseModel):
    question: str = Field(min_length=1)
    document_id: str | None = None
    version_id: str = "v1"
    audience: RagAudience = "bank_employee"
    top_k: int = Field(default=5, ge=1, le=20)
    model_override: str | None = None
    request_id: str | None = None
    chat_id: str | None = None
    source_fragments: list[RagFragmentInput] | None = None
    chunks: list[DocumentChunkForAI] | None = None


class CreateNotificationsInput(BaseModel):
    event_card: RegulatoryEventCard
    client_relevance: list[ClientRelevance]
    document_analysis: DocumentAnalysis | None = None
    request_id: str | None = None


class MockSendNotificationInput(BaseModel):
    notification_id: str | None = None
    document_id: str
    version_id: str = "v1"
    event_id: str | None = None
    client_id: str = Field(min_length=1)
    client_name: str | None = None
    notification: NotificationDraft
    channel: NotificationMockChannel = "mock"
    source_chunk_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class AIServiceValidationError(ValueError):
    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or [message]


class RegRadarAIService:
    """Thin orchestrator hiding providers, engines and repositories from callers."""

    def __init__(
        self,
        *,
        config_getter: Callable[[], GatewayConfig] = get_config,
        document_repo=document_repository,
        event_repo=event_repository,
        notification_repo=notification_repository,
        rag_chat_repo=rag_chat_repository,
        full_analysis_runner: Callable[..., FullAIAnalysisResponse] = full_ai_analysis,
        document_analyzer: Callable[..., DocumentAnalysis] = analyze_document_with_safe_fallback,
        rag_runner: Callable[..., RagAnswer] = ask_rag,
    ) -> None:
        self._config_getter = config_getter
        self.document_repository = document_repo
        self.event_repository = event_repo
        self.notification_repository = notification_repo
        self.rag_chat_repository = rag_chat_repo
        self._full_analysis_runner = full_analysis_runner
        self._document_analyzer = document_analyzer
        self._rag_runner = rag_runner

    @staticmethod
    def _default_document_id(text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        return f"analysis_{digest}"

    @staticmethod
    def _attach_notification_context(
        drafts: list[NotificationDraft],
        document_id: str,
        version_id: str,
        chunk_ids: list[str],
    ) -> None:
        for draft in drafts:
            draft.notification_id = draft.notification_id or str(uuid4())
            draft.document_id = document_id
            draft.version_id = version_id
            draft.source_chunk_ids = list(chunk_ids)

    async def analyze_document(
        self,
        payload: AnalyzeDocumentInput,
        *,
        endpoint: str = "service:analyze_document",
    ) -> DocumentAnalysis:
        result = self._document_analyzer(
            payload.text,
            payload.model_override,
            request_id=payload.request_id,
            endpoint=endpoint,
        )
        if payload.title and payload.title.strip():
            result.title = payload.title.strip()
        return result

    async def run_full_analysis(
        self,
        payload: FullAnalysisInput,
        *,
        endpoint: str = "service:run_full_analysis",
    ) -> FullAIAnalysisResponse:
        document_id = payload.document_id or self._default_document_id(payload.text)
        version_id = payload.version_id
        result = self._full_analysis_runner(
            payload.text,
            payload.client_profiles,
            payload.model_override,
            payload.request_id,
            endpoint,
            payload.use_seed_fallback,
        )
        if payload.title and payload.title.strip():
            result.document_analysis.title = payload.title.strip()
        result.analysis_metadata.context_document_id = document_id
        result.analysis_metadata.context_version_id = version_id
        chunks = chunk_text_for_document(payload.text)
        self._attach_notification_context(
            result.notification_drafts,
            document_id,
            version_id,
            [chunk.chunk_id for chunk in chunks],
        )
        persistence = persist_document(
            document_id=document_id,
            version_id=version_id,
            text=payload.text,
            chunks=chunks,
            filename=payload.filename,
            content_type=payload.content_type,
            source_url=payload.source_url,
            metadata={
                "source": payload.source,
                "domain": result.document_analysis.domain,
                "relevant_client_ids": [item.client_id for item in result.client_relevance],
            },
        )
        apply_persistence_metadata(result.analysis_metadata, persistence)
        save_document_context(
            document_id,
            version_id,
            context_fragments_from_sources(
                document_id,
                version_id,
                chunks=chunks,
                text_fragments=result.document_analysis.source_fragments,
            ),
        )
        return result

    async def create_event_card(
        self,
        payload: CreateEventCardInput,
        *,
        endpoint: str = "service:create_event_card",
    ) -> RegulatoryEventCard:
        chunks = chunk_text_for_document(payload.text)
        document_id = payload.document_id or self._default_document_id(payload.text)
        request = CreateEventCardFromDocumentRequest(
            document_id=document_id,
            version_id=payload.version_id,
            chunks=chunks,
            metadata=DocumentMetadataForAI(
                title=payload.title,
                source=payload.source,
                original_url=payload.source_url,
            ),
            source_type=payload.source_type,
            source_url=payload.source_url,
            client_profiles=payload.client_profiles,
            model_override=payload.model_override,
            request_id=payload.request_id,
            use_seed_fallback=payload.use_seed_fallback,
        )
        response = await self.create_event_card_from_document(
            request,
            endpoint=endpoint,
            request_id=payload.request_id,
            filename=payload.filename,
            content_type=payload.content_type,
        )
        return response.event_card

    async def create_event_card_from_document(
        self,
        payload: CreateEventCardFromDocumentRequest,
        *,
        endpoint: str = "service:create_event_card_from_document",
        request_id: str | None = None,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> CreateEventCardFromDocumentResponse:
        # The existing adapter owns evidence-to-chunk linkage. The facade owns
        # orchestration/persistence around it.
        response = create_event_card_from_document_payload(
            payload,
            request_id=request_id or payload.request_id,
            endpoint=endpoint,
        )
        card = response.event_card
        card.analysis_metadata.context_document_id = payload.document_id
        card.analysis_metadata.context_version_id = payload.version_id
        if request_id or payload.request_id:
            card.analysis_metadata.request_id = request_id or payload.request_id
        self._attach_notification_context(
            card.notification_drafts,
            payload.document_id,
            payload.version_id,
            [chunk.chunk_id for chunk in payload.chunks],
        )
        sorted_chunks = sorted(payload.chunks, key=lambda item: item.order_index)
        text = "\n\n".join(chunk.text for chunk in sorted_chunks)
        document_persistence = persist_document(
            document_id=payload.document_id,
            version_id=payload.version_id,
            text=text,
            chunks=payload.chunks,
            filename=filename,
            content_type=content_type,
            source_url=payload.source_url or payload.metadata.original_url,
            metadata={
                **payload.metadata.model_dump(mode="json", exclude_none=True),
                "domain": card.document_analysis.domain,
                "relevant_client_ids": [item.client_id for item in card.client_relevance],
            },
        )
        apply_persistence_metadata(card.analysis_metadata, document_persistence)
        event_persistence = persist_event(card, payload.document_id, payload.version_id)
        apply_persistence_metadata(card.analysis_metadata, event_persistence)
        save_document_context(
            payload.document_id,
            payload.version_id,
            context_fragments_from_sources(
                payload.document_id,
                payload.version_id,
                chunks=payload.chunks,
                evidence=card.evidence_fragments,
            ),
        )
        return response

    async def ask_rag(
        self,
        payload: RagAskInput,
        *,
        endpoint: str = "service:ask_rag",
    ) -> RagAnswer:
        return self._rag_runner(
            RagAskRequest(**payload.model_dump()),
            endpoint=endpoint,
        )

    async def create_notifications(
        self,
        payload: CreateNotificationsInput,
    ) -> list[NotificationDraft]:
        relevant_ids = {item.client_id for item in payload.client_relevance}
        context = payload.document_analysis or payload.event_card
        result: list[NotificationDraft] = []
        for draft in payload.event_card.notification_drafts:
            if draft.client_id not in relevant_ids:
                continue
            safe_draft = ensure_notification_disclaimer(draft)
            if not validate_notification_can_be_sent(
                safe_draft,
                payload.client_relevance,
                context,
            ):
                result.append(safe_draft)
        return result

    async def mock_send_notification(
        self,
        payload: MockSendNotificationInput,
    ) -> NotificationMockSendResponse:
        notification = ensure_notification_disclaimer(payload.notification)
        if notification.client_id != payload.client_id:
            raise AIServiceValidationError(
                "notification client_id does not match request client_id"
            )
        event_card = None
        if payload.event_id:
            event_card = self.event_repository.get_event_card(payload.event_id)
        if event_card is None:
            event_record = self.event_repository.get_latest_event_by_document(
                payload.document_id,
                payload.version_id,
            )
            if event_record:
                event_card = event_record.get("event_card")
        document = self.document_repository.get_document(
            payload.document_id,
            payload.version_id,
        )
        client_relevance = None
        safety_context = event_card
        if event_card:
            client_relevance = event_card.get("client_relevance") or []
        elif document:
            relevant_ids = document.metadata.get("relevant_client_ids")
            if isinstance(relevant_ids, list):
                client_relevance = [{"client_id": value} for value in relevant_ids]
            safety_context = {"domain": document.metadata.get("domain")}
        safety_errors = validate_notification_can_be_sent(
            notification,
            client_relevance,
            safety_context,
        )
        if safety_errors:
            raise AIServiceValidationError(
                "Notification mock-send blocked by safety validation",
                safety_errors,
            )

        sent_at = datetime.now(timezone.utc).isoformat()
        notification_id = (
            payload.notification_id
            or notification.notification_id
            or str(uuid4())
        )
        delivery_id = str(uuid4())
        source_chunk_ids = payload.source_chunk_ids or notification.source_chunk_ids
        record = self.notification_repository.NotificationDeliveryRecord(
            notification_id=notification_id,
            delivery_id=delivery_id,
            event_id=payload.event_id,
            document_id=payload.document_id,
            version_id=payload.version_id,
            client_id=payload.client_id,
            client_name=payload.client_name or notification.client_name,
            notification_title=notification.title,
            channel=payload.channel,
            status="sent_mock",
            priority=notification.priority,
            disclaimer=notification.disclaimer,
            source_link=notification.source_link,
            source_chunk_ids=source_chunk_ids,
            sent_at=sent_at,
            payload_preview={
                "short_message": notification.short_message,
                "full_message": notification.full_message,
            },
            metadata={
                **payload.metadata,
                "request_id": payload.request_id,
                "delivery_mode": "mock_only",
            },
        )
        saved = self.notification_repository.save_delivery(record)
        warnings = [] if saved else [
            "persistence warning: notification delivery was not saved"
        ]
        return NotificationMockSendResponse(
            delivery_id=delivery_id,
            notification_id=notification_id,
            channel=payload.channel,
            sent_at=sent_at,
            client_id=payload.client_id,
            client_name=payload.client_name or notification.client_name,
            document_id=payload.document_id,
            version_id=payload.version_id,
            saved=saved,
            disclaimer=notification.disclaimer,
            metadata={
                "delivery_mode": "mock_only",
                "request_id": payload.request_id,
                "notification_saved": saved,
                "warnings": warnings,
            },
        )

    def get_models(self) -> AIModelsResponse:
        config = self._config_getter()
        return AIModelsResponse(
            provider=config.llm_provider.casefold().strip(),
            default_model=config.polza_model,
            allowed_models=public_model_catalog(config),
        )

    def healthcheck(self) -> dict[str, Any]:
        config = self._config_getter()
        storage_paths = {
            "documents": self.document_repository.DOCUMENTS_PATH,
            "chunks": self.document_repository.CHUNKS_PATH,
            "events": self.event_repository.EVENTS_PATH,
            "rag_chats": self.rag_chat_repository.RAG_CHATS_PATH,
            "notifications": self.notification_repository.NOTIFICATIONS_PATH,
        }
        storage = {
            name: "ok"
            if path.exists() or path.parent.exists() or path.parent.parent.exists()
            else "unavailable"
            for name, path in storage_paths.items()
        }
        prompts = {
            name: "ok" if (PROMPTS_DIR / f"{name}.md").is_file() else "missing"
            for name in ("document_analysis_v1", "rag_answer_v1")
        }
        healthy = all(value == "ok" for value in storage.values()) and all(
            value == "ok" for value in prompts.values()
        )
        return {
            "status": "ok" if healthy else "degraded",
            "provider_mode": config.llm_provider.casefold().strip(),
            "default_model": config.active_model,
            "allowed_models": public_model_catalog(config),
            "storage": storage,
            "prompts": prompts,
        }
