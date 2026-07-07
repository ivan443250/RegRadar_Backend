"""Production compatibility endpoints exposed to the .NET backend."""

from __future__ import annotations

import asyncio
import logging
import os

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ...ai.model_catalog import ModelNotAllowedError
from ...ai.reg_radar_ai_service import AIServiceValidationError, RegRadarAIService
from ...ai.service_factory import get_reg_radar_ai_service
from .backend_contract import BackendContractError, BackendContractService
from .schemas import (
    BackendContractAnalyzeRequest,
    BackendContractAnalyzeResponse,
    BackendContractHealthResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def get_backend_contract_service(
    ai_service: RegRadarAIService = Depends(get_reg_radar_ai_service),
) -> BackendContractService:
    return BackendContractService(ai_service)


def _timeout_seconds() -> int:
    try:
        return max(1, int(os.getenv("BACKEND_CONTRACT_TIMEOUT_SECONDS", "120")))
    except ValueError:
        return 120


@router.post("/analyze", response_model=BackendContractAnalyzeResponse)
async def analyze(
    request: BackendContractAnalyzeRequest,
    service: BackendContractService = Depends(get_backend_contract_service),
):
    try:
        # Existing AI orchestration is synchronous internally. A worker thread
        # lets the HTTP layer enforce the .NET backend's 120-second deadline.
        return await asyncio.wait_for(
            asyncio.to_thread(lambda: asyncio.run(service.analyze(request))),
            timeout=_timeout_seconds(),
        )
    except BackendContractError as exc:
        logger.warning("/analyze request rejected: %s", exc)
        return JSONResponse(status_code=exc.status_code, content={"error": str(exc)})
    except (ModelNotAllowedError, AIServiceValidationError, ValueError) as exc:
        logger.warning("/analyze validation failed: %s", exc)
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except TimeoutError:
        message = f"AI analysis exceeded {_timeout_seconds()} seconds"
        logger.error(message)
        return JSONResponse(status_code=504, content={"error": message})
    except Exception as exc:  # pragma: no cover - defensive HTTP boundary
        logger.exception("Unexpected /analyze failure")
        return JSONResponse(
            status_code=500,
            content={"error": f"AI analysis failed: {type(exc).__name__}"},
        )


@router.get("/health", response_model=BackendContractHealthResponse)
def health(
    ai_service: RegRadarAIService = Depends(get_reg_radar_ai_service),
):
    report = ai_service.healthcheck()
    return BackendContractHealthResponse(
        status=report["status"],
        provider_mode=report["provider_mode"],
        default_model=report["default_model"],
        prompts=list(report["prompts"]),
        storage=report["storage"],
    )
