"""FastAPI integration endpoints consumed by the main RegRadar.Api backend."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from ...ai.reg_radar_ai_service import RegRadarAIService
from ...ai.service_factory import get_reg_radar_ai_service
from .client import MainBackendApiClient, MainBackendApiError
from .mappers import map_main_client_profile_to_ai
from .schemas import (
    IntegrationAnalyzeDocumentRequest,
    IntegrationAnalyzeDocumentResponse,
    MainBackendClientProfilesDebugResponse,
    MainBackendIntegrationHealthResponse,
)
from .service import MainBackendIntegrationError, MainBackendIntegrationService


router = APIRouter()


def _truthy(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"1", "true", "yes", "on"}


def get_main_backend_client() -> MainBackendApiClient | None:
    base_url = os.getenv("MAIN_BACKEND_URL", "").strip()
    if not base_url:
        return None
    raw_timeout = os.getenv("MAIN_BACKEND_TIMEOUT_SECONDS", "30")
    try:
        timeout = int(raw_timeout)
    except ValueError:
        timeout = 30
    return MainBackendApiClient(base_url, timeout=max(timeout, 1))


def get_main_backend_integration_service(
    ai_service: RegRadarAIService = Depends(get_reg_radar_ai_service),
    client: MainBackendApiClient | None = Depends(get_main_backend_client),
) -> MainBackendIntegrationService:
    return MainBackendIntegrationService(
        ai_service,
        client,
        allow_seed_fallback=_truthy(
            os.getenv("MAIN_BACKEND_ALLOW_SEED_FALLBACK")
        ),
    )


@router.post(
    "/analyze-document",
    response_model=IntegrationAnalyzeDocumentResponse,
)
async def analyze_document(
    request: IntegrationAnalyzeDocumentRequest,
    service: MainBackendIntegrationService = Depends(
        get_main_backend_integration_service
    ),
):
    try:
        return await service.analyze_document_for_main_backend(request)
    except MainBackendIntegrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get(
    "/client-profiles",
    response_model=MainBackendClientProfilesDebugResponse,
)
async def client_profiles(
    client: MainBackendApiClient | None = Depends(get_main_backend_client),
):
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="MAIN_BACKEND_URL is not configured",
        )
    try:
        profiles = await client.get_client_profiles()
    except MainBackendApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return MainBackendClientProfilesDebugResponse(
        main_profiles=profiles,
        ai_profiles=[
            map_main_client_profile_to_ai(item).model_dump(mode="json")
            for item in profiles
        ],
    )


@router.get(
    "/health",
    response_model=MainBackendIntegrationHealthResponse,
)
async def health(
    ai_service: RegRadarAIService = Depends(get_reg_radar_ai_service),
    client: MainBackendApiClient | None = Depends(get_main_backend_client),
):
    notes: list[str] = []
    reachable = False
    url = client.base_url if client else None
    if client is None:
        notes.append(
            "MAIN_BACKEND_URL is not configured; request-provided clientProfiles still work"
        )
    else:
        reachable, error = await client.check_reachable()
        if error:
            notes.append(error)
    return MainBackendIntegrationHealthResponse(
        main_backend_url=url,
        main_backend_reachable=reachable,
        ai_service_health=ai_service.healthcheck(),
        notes=notes,
    )
