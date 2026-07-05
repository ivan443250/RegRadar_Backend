"""Orchestration between Main Backend DTOs and RegRadarAIService."""

from __future__ import annotations

from ...ai.reg_radar_ai_service import CreateEventCardInput, RegRadarAIService
from ...ai.schemas import ClientProfileForAI
from .client import MainBackendApiClient, MainBackendApiError
from .mappers import (
    map_ai_client_relevance_to_main_impacts,
    map_ai_event_card_to_main_payload,
    map_main_client_profile_to_ai,
    map_notification_draft_to_main_payload,
)
from .schemas import (
    IntegrationAnalyzeDocumentRequest,
    IntegrationAnalyzeDocumentResponse,
    MainBackendDocumentForAI,
)


class MainBackendIntegrationError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class MainBackendIntegrationService:
    def __init__(
        self,
        ai_service: RegRadarAIService,
        main_backend_client: MainBackendApiClient | None = None,
        *,
        allow_seed_fallback: bool = False,
    ) -> None:
        self.ai_service = ai_service
        self.main_backend_client = main_backend_client
        self.allow_seed_fallback = allow_seed_fallback

    async def _resolve_client_profiles(
        self,
        request: IntegrationAnalyzeDocumentRequest,
    ) -> list[ClientProfileForAI] | None:
        if request.client_profiles is not None:
            if request.client_profiles:
                return [
                    map_main_client_profile_to_ai(item)
                    for item in request.client_profiles
                ]
            if self.allow_seed_fallback:
                return None
            raise MainBackendIntegrationError(
                "clientProfiles is empty. Pass at least one profile or explicitly "
                "enable MAIN_BACKEND_ALLOW_SEED_FALLBACK."
            )

        if self.main_backend_client is not None:
            try:
                profiles = await self.main_backend_client.get_client_profiles()
            except MainBackendApiError as exc:
                if self.allow_seed_fallback:
                    return None
                raise MainBackendIntegrationError(str(exc), status_code=502) from exc
            if profiles:
                return [map_main_client_profile_to_ai(item) for item in profiles]

        if self.allow_seed_fallback:
            return None

        raise MainBackendIntegrationError(
            "Cannot resolve client profiles: MAIN_BACKEND_URL is not configured "
            "and clientProfiles were not provided. "
            "Pass clientProfiles or explicitly enable MAIN_BACKEND_ALLOW_SEED_FALLBACK.",
            status_code=503,
        )

    async def analyze_document_for_main_backend(
        self,
        request: IntegrationAnalyzeDocumentRequest,
    ) -> IntegrationAnalyzeDocumentResponse:
        if not request.document.text.strip():
            raise MainBackendIntegrationError("document.text must not be empty")

        profiles = await self._resolve_client_profiles(request)
        card = await self.ai_service.create_event_card(
            CreateEventCardInput(
                text=request.document.text,
                document_id=request.document.id,
                version_id="v1",
                title=request.document.title,
                source_url=request.document.original_url,
                client_profiles=profiles,
                model_override=request.model_override,
                request_id=request.request_id,
                source="main_backend_integration",
                source_type="main_backend_document",
            ),
            endpoint="/api/integration/main-backend/analyze-document",
        )

        event_payload = map_ai_event_card_to_main_payload(
            card,
            request.document.id,
        )
        impacts = map_ai_client_relevance_to_main_impacts(card.client_relevance)
        notifications = [
            map_notification_draft_to_main_payload(item)
            for item in card.notification_drafts
        ]
        evidence = [item.model_dump(mode="json") for item in card.evidence_fragments]
        metadata = card.analysis_metadata.model_dump(mode="json")
        return IntegrationAnalyzeDocumentResponse(
            document_id=request.document.id,
            regulatory_event=event_payload,
            client_impacts=impacts,
            notification_drafts=notifications,
            evidence=evidence,
            rag_context={
                "documentId": request.document.id,
                "versionId": "v1",
                "chunkIds": _unique_chunk_ids(evidence),
                "sourceFragments": evidence,
            },
            ai_metadata=metadata,
            raw_ai_result=card.model_dump(mode="json"),
        )

    async def analyze_existing_document_id(
        self,
        document_id: str,
        text: str | None = None,
        *,
        model_override: str | None = None,
        request_id: str | None = None,
    ) -> IntegrationAnalyzeDocumentResponse:
        document = None
        if self.main_backend_client is not None:
            try:
                document = await self.main_backend_client.get_document(document_id)
            except MainBackendApiError as exc:
                raise MainBackendIntegrationError(str(exc), status_code=502) from exc

        if text is None or not text.strip():
            if self.main_backend_client is None:
                raise MainBackendIntegrationError(
                    "Document text was not provided and MAIN_BACKEND_URL is not configured."
                )
            try:
                text = await self.main_backend_client.get_document_text(document_id)
            except MainBackendApiError as exc:
                raise MainBackendIntegrationError(str(exc), status_code=502) from exc

        request = IntegrationAnalyzeDocumentRequest(
            document=MainBackendDocumentForAI(
                id=document_id,
                title=document.title if document else document_id,
                text=text,
                original_url=document.original_url if document else None,
                regulator=document.regulator if document else None,
                document_type=document.document_type if document else None,
                publication_date=document.publication_date if document else None,
            ),
            model_override=model_override,
            request_id=request_id,
        )
        return await self.analyze_document_for_main_backend(request)


def _unique_chunk_ids(evidence: list[dict]) -> list[str]:
    return list(
        dict.fromkeys(
            item["chunk_id"]
            for item in evidence
            if item.get("chunk_id")
        )
    )
