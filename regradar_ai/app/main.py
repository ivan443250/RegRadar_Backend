import json
import logging
import re
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, TypeAdapter, ValidationError

from .models import (
    AnalyzeRequest,
    AnalyzeResponse,
    AffectedClientResponse,
    RegulatoryEventResponse,
    NotificationResponse,
)
from .services.parser import parse_text
from .services.analyzer import analyze
from .services.matcher import match_clients, generate_notifications
from .ai.schemas import (
    CreateEventCardFromDocumentRequest,
    CreateEventCardFromDocumentResponse,
    CreateEventCardRequest,
    CreateEventCardResponse,
    DocumentAnalysis,
    DocumentMetadataForAI,
    ClientProfileForAI,
    FullAIAnalysisRequest,
    FullAIAnalysisResponse,
    NonEmptyText,
    UploadAnalysisResponse,
    UploadCreateCardResponse,
    AIModelsResponse,
    RagAnswer,
    RagAskRequest,
    NotificationMockSendRequest,
    NotificationMockSendResponse,
)
from .ai.gateway.gateway import LLMGateway
from .ai.model_catalog import ModelNotAllowedError
from .ai.llm_call_logger import LLMCallLogRecord, read_recent_llm_calls
from .storage import (
    document_repository,
    event_repository,
    notification_repository,
    rag_chat_repository,
)
from .ai.reg_radar_ai_service import (
    AIServiceValidationError,
    AnalyzeDocumentInput,
    CreateEventCardInput,
    FullAnalysisInput,
    MockSendNotificationInput,
    RagAskInput,
    RegRadarAIService,
)
from .ai.service_factory import get_reg_radar_ai_service
from .services.document_text_extractor import (
    MAX_FILE_SIZE_BYTES,
    DocumentExtractionError,
    ExtractedDocumentText,
    extract_text_from_upload,
)
from .services.document_chunker import chunk_text_for_document
from .integrations.main_backend.router import router as main_backend_integration_router
from .integrations.main_backend.contract_router import router as backend_contract_router

app = FastAPI(title="RegRadar", version="0.1.0")
logger = logging.getLogger(__name__)
app.include_router(
    main_backend_integration_router,
    prefix="/api/integration/main-backend",
    tags=["main-backend-integration"],
)
app.include_router(backend_contract_router, tags=["backend-contract"])


@app.exception_handler(ModelNotAllowedError)
async def model_not_allowed_handler(_, exc: ModelNotAllowedError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(AIServiceValidationError)
async def ai_service_validation_handler(_, exc: AIServiceValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "detail": {
                "message": str(exc),
                "errors": exc.errors,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    if request.url.path == "/analyze":
        issues = [
            f"{'.'.join(str(item) for item in error['loc'] if item != 'body')}: "
            f"{error['msg']}"
            for error in exc.errors()
        ]
        logger.warning("/analyze schema validation failed: %s", "; ".join(issues))
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid request: {'; '.join(issues)}"},
        )
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": exc.errors()}),
    )


@app.get("/api/ai/health")
def ai_health(service: RegRadarAIService = Depends(get_reg_radar_ai_service)):
    return service.healthcheck()


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_document(req: AnalyzeRequest):
    text = parse_text(req.text)
    event = analyze(text)
    matched = match_clients(event)
    notifications = generate_notifications(matched, event)

    return AnalyzeResponse(
        event=RegulatoryEventResponse(
            title=event.title,
            summary=event.summary,
            category=event.category,
            impact=event.impact,
            impact_reason=event.impact_reason,
        ),
        affected_clients=[
            AffectedClientResponse(
                name=mc.client.name,
                segment=mc.client.segment,
                match_reason=mc.match_reason,
            )
            for mc in matched
        ],
        notifications=[
            NotificationResponse(
                client_name=n.client_name,
                message=n.message,
            )
            for n in notifications
        ],
    )


@app.post("/api/ai/full-analysis", response_model=FullAIAnalysisResponse)
async def ai_full_analysis(
    req: FullAIAnalysisRequest,
    service: RegRadarAIService = Depends(get_reg_radar_ai_service),
):
    """Полный AI-анализ регуляторного текста (mock AI).

    Возвращает структурированный результат: анализ документа,
    оценку влияния, релевантных клиентов и проекты уведомлений.
    """
    return await service.run_full_analysis(
        FullAnalysisInput(
            text=req.text,
            client_profiles=req.client_profiles,
            model_override=req.model_override,
            request_id=req.request_id,
        ),
        endpoint="/api/ai/full-analysis",
    )


@app.get("/api/ai/models", response_model=AIModelsResponse)
def ai_models(service: RegRadarAIService = Depends(get_reg_radar_ai_service)):
    return service.get_models()


def _parse_client_profiles_json(
    client_profiles_json: str | None,
) -> list[ClientProfileForAI] | None:
    if client_profiles_json is None or not client_profiles_json.strip():
        return None
    try:
        raw_profiles = json.loads(client_profiles_json)
        return TypeAdapter(list[ClientProfileForAI]).validate_python(raw_profiles)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid client_profiles_json: {exc}",
        ) from exc


@app.post(
    "/api/documents/upload-analysis",
    response_model=UploadAnalysisResponse,
)
async def upload_document_analysis(
    file: UploadFile = File(...),
    client_profiles_json: str | None = Form(None),
    model_override: str | None = Form(None),
    service: RegRadarAIService = Depends(get_reg_radar_ai_service),
):
    """Extract TXT/PDF text and run the existing full analysis pipeline."""
    extracted = await _extract_document_upload(file)
    client_profiles = _parse_client_profiles_json(client_profiles_json)
    document_id = _default_upload_document_id(extracted.filename)
    version_id = "v1"
    analysis_result = await service.run_full_analysis(
        FullAnalysisInput(
            text=extracted.text,
            document_id=document_id,
            version_id=version_id,
            client_profiles=client_profiles,
            model_override=model_override,
            filename=extracted.filename,
            content_type=extracted.content_type,
            source="upload_analysis",
        ),
        endpoint="/api/documents/upload-analysis",
    )
    return UploadAnalysisResponse(
        filename=extracted.filename,
        content_type=extracted.content_type,
        extracted_text_length=extracted.extracted_text_length,
        document_id=document_id,
        version_id=version_id,
        analysis_result=analysis_result,
    )


async def _extract_document_upload(file: UploadFile) -> ExtractedDocumentText:
    """Read one bounded upload and translate extractor errors to HTTP errors."""
    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    try:
        return extract_text_from_upload(
            filename=file.filename or "",
            content_type=file.content_type,
            content=content,
        )
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    finally:
        await file.close()


def _default_upload_document_id(filename: str) -> str:
    stem = Path(filename).stem.casefold()
    safe_stem = re.sub(r"[^\w-]+", "_", stem).strip("_") or "document"
    return f"upload_{safe_stem}"


@app.post(
    "/api/documents/upload-create-card",
    response_model=UploadCreateCardResponse,
)
async def upload_create_event_card(
    file: UploadFile = File(...),
    document_id: str | None = Form(None),
    version_id: str | None = Form(None),
    title: str | None = Form(None),
    source_url: str | None = Form(None),
    client_profiles_json: str | None = Form(None),
    model_override: str | None = Form(None),
    service: RegRadarAIService = Depends(get_reg_radar_ai_service),
):
    """Extract and chunk a file, then use the existing document-card flow."""
    extracted = await _extract_document_upload(file)
    effective_document_id = (
        document_id.strip()
        if document_id and document_id.strip()
        else _default_upload_document_id(extracted.filename)
    )
    effective_version_id = (
        version_id.strip() if version_id and version_id.strip() else "v1"
    )
    explicit_title = title.strip() if title and title.strip() else None
    effective_source_url = (
        source_url.strip() if source_url and source_url.strip() else None
    )
    chunks = chunk_text_for_document(extracted.text)
    client_profiles = _parse_client_profiles_json(client_profiles_json)
    card_response = await service.create_event_card_from_document(
        CreateEventCardFromDocumentRequest(
            document_id=effective_document_id,
            version_id=effective_version_id,
            chunks=chunks,
            metadata=DocumentMetadataForAI(
                title=explicit_title,
                source="upload",
                original_url=effective_source_url,
            ),
            source_type="uploaded_file",
            source_url=effective_source_url,
            client_profiles=client_profiles,
            model_override=model_override,
        ),
        endpoint="/api/documents/upload-create-card",
        filename=extracted.filename,
        content_type=extracted.content_type,
    )
    if not card_response.event_card.title.strip():
        card_response.event_card.title = extracted.filename
    return UploadCreateCardResponse(
        filename=extracted.filename,
        content_type=extracted.content_type,
        extracted_text_length=extracted.extracted_text_length,
        document_id=effective_document_id,
        version_id=effective_version_id,
        chunks_count=len(chunks),
        card=card_response,
    )


@app.post("/api/events/create-card", response_model=CreateEventCardResponse)
async def create_regulatory_event_card(
    req: CreateEventCardRequest,
    service: RegRadarAIService = Depends(get_reg_radar_ai_service),
):
    """Создать центральную карточку регуляторного события (mock AI)."""
    card = await service.create_event_card(
        CreateEventCardInput(
            text=req.text,
            source_type=req.source_type or "uploaded_text",
            source_url=req.source_url,
            model_override=req.model_override,
        ),
        endpoint="/api/events/create-card",
    )
    return CreateEventCardResponse(event_card=card)


@app.post(
    "/api/events/create-card-from-document",
    response_model=CreateEventCardFromDocumentResponse,
)
async def create_regulatory_event_card_from_document(
    req: CreateEventCardFromDocumentRequest,
    service: RegRadarAIService = Depends(get_reg_radar_ai_service),
):
    """Создать карточку из будущего контракта document/version/chunks."""
    return await service.create_event_card_from_document(
        req,
        endpoint="/api/events/create-card-from-document",
    )


@app.post("/api/rag/ask", response_model=RagAnswer)
async def rag_ask(
    req: RagAskRequest,
    service: RegRadarAIService = Depends(get_reg_radar_ai_service),
):
    return await service.ask_rag(
        RagAskInput(**req.model_dump()),
        endpoint="/api/rag/ask",
    )


class GatewayTestRequest(BaseModel):
    text: NonEmptyText
    request_id: str | None = None


@app.post("/api/ai/document-analysis", response_model=DocumentAnalysis)
async def document_analysis_via_gateway(
    req: FullAIAnalysisRequest,
    service: RegRadarAIService = Depends(get_reg_radar_ai_service),
):
    """Проанализировать документ через prompt management и LLM Gateway."""
    return await service.analyze_document(
        AnalyzeDocumentInput(
            text=req.text,
            model_override=req.model_override,
            request_id=req.request_id,
        ),
        endpoint="/api/ai/document-analysis",
    )


@app.post("/api/ai/gateway-test", response_model=DocumentAnalysis)
def gateway_test(req: GatewayTestRequest):
    """Технический endpoint для проверки LLM Gateway.

    Использует LLMGateway + MockLLMProvider для анализа текста
    и возвращает DocumentAnalysis.
    """
    gateway = LLMGateway()
    return gateway.generate_structured(
        prompt=req.text,
        response_model=DocumentAnalysis,
        metadata={
            "request_id": req.request_id,
            "endpoint": "/api/ai/gateway-test",
            "operation": "gateway_test",
            "input_chars": len(req.text),
        },
    )


@app.get("/api/debug/llm-calls", response_model=list[LLMCallLogRecord])
def debug_llm_calls(limit: int = Query(default=50, ge=1, le=200)):
    """Demo/dev-only view of the privacy-safe local AI audit trail."""
    return read_recent_llm_calls(limit)


@app.get("/api/debug/documents")
def debug_documents(limit: int = Query(default=50, ge=1, le=200)):
    return [record.model_dump(mode="json") for record in document_repository.list_documents(limit)]


@app.get("/api/debug/documents/{document_id}/chunks")
def debug_document_chunks(
    document_id: str,
    version_id: str = "v1",
):
    return [
        record.model_dump(mode="json")
        for record in document_repository.get_chunks(document_id, version_id)
    ]


@app.get("/api/debug/events")
def debug_events(limit: int = Query(default=50, ge=1, le=200)):
    return event_repository.list_event_cards(limit)


@app.get("/api/debug/rag-chats")
def debug_rag_chats(
    document_id: str | None = None,
    version_id: str = "v1",
    limit: int = Query(default=20, ge=1, le=200),
):
    if document_id:
        return rag_chat_repository.list_rag_history(
            document_id,
            version_id,
            limit,
        )
    return rag_chat_repository.get_recent_rag_chats(limit)


@app.post(
    "/api/notifications/mock-send",
    response_model=NotificationMockSendResponse,
)
async def mock_send_notification(
    req: NotificationMockSendRequest,
    service: RegRadarAIService = Depends(get_reg_radar_ai_service),
):
    return await service.mock_send_notification(
        MockSendNotificationInput(**req.model_dump())
    )


@app.get("/api/debug/notifications")
def debug_notifications(limit: int = Query(default=50, ge=1, le=200)):
    return notification_repository.list_deliveries(limit)


@app.get("/api/debug/notifications/by-document/{document_id}")
def debug_notifications_by_document(
    document_id: str,
    version_id: str = "v1",
    limit: int = Query(default=50, ge=1, le=200),
):
    return notification_repository.list_deliveries_by_document(
        document_id,
        version_id,
        limit,
    )


@app.get("/api/debug/notifications/by-client/{client_id}")
def debug_notifications_by_client(
    client_id: str,
    limit: int = Query(default=50, ge=1, le=200),
):
    return notification_repository.list_deliveries_by_client(client_id, limit)
