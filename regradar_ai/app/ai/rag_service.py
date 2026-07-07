"""Source-grounded RAG-lite orchestration through the existing LLM Gateway."""

import json
import re
from uuid import uuid4

from .constants import DEFAULT_MODEL_VERSION
from .gateway.config import get_config
from .gateway.errors import (
    LLMProviderConfigError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMResponseParsingError,
    LLMResponseValidationError,
)
from .gateway.gateway import LLMGateway
from .model_catalog import resolve_model_selection
from .prompt_loader import PromptNotFoundError, PromptRenderError, load_prompt
from .rag_context_store import get_document_context
from .rag_retrieval import retrieve_top_fragments
from .schemas import (
    AnalysisMetadata,
    RagAnswer,
    RagAskRequest,
    RagFragmentInput,
    RagLLMOutput,
    RagSourceFragment,
)
from .llm_call_logger import LLMCallLogRecord, estimate_tokens, log_llm_call
from ..storage import document_repository, rag_chat_repository


RAG_PROMPT_VERSION = "rag_answer_v1"
NO_DATA_ANSWER = "Нет данных в базе по этому вопросу."
BANK_NOTICE = (
    "Ответ носит информационный характер и требует проверки профильным специалистом."
)
CLIENT_NOTICE = "Это информационное уведомление и не является юридической консультацией."

RAG_FALLBACK_ERRORS = (
    LLMProviderConfigError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMResponseParsingError,
    LLMResponseValidationError,
    PromptNotFoundError,
    PromptRenderError,
)


def _safety_notice(audience: str) -> str:
    return CLIENT_NOTICE if audience == "client" else BANK_NOTICE


def _request_fragments(request: RagAskRequest) -> list[RagFragmentInput]:
    fragments = list(request.source_fragments or [])
    if request.chunks:
        document_id = request.document_id or "request_document"
        fragments.extend(
            RagFragmentInput(
                text=chunk.text,
                document_id=document_id,
                version_id=request.version_id,
                chunk_id=chunk.chunk_id,
                role="document_chunk",
            )
            for chunk in request.chunks
        )
    if not fragments and request.document_id:
        stored_chunks = document_repository.get_chunks(
            request.document_id,
            request.version_id,
        )
        fragments = [
            RagFragmentInput(
                text=chunk.text,
                document_id=chunk.document_id,
                version_id=chunk.version_id,
                chunk_id=chunk.chunk_id,
                role="stored_document_chunk",
            )
            for chunk in stored_chunks
        ]
    if not fragments and request.document_id:
        fragments = get_document_context(request.document_id, request.version_id)
    return fragments


def _persist_rag_answer(request: RagAskRequest, answer: RagAnswer) -> RagAnswer:
    first_source = answer.source_fragments[0] if answer.source_fragments else None
    first_request_source = (
        request.source_fragments[0] if request.source_fragments else None
    )
    document_id = (
        request.document_id
        or (first_source.document_id if first_source else None)
        or (first_request_source.document_id if first_request_source else None)
        or "unknown"
    )
    version_id = (
        request.version_id
        or (first_source.version_id if first_source else None)
        or "v1"
    )
    record = rag_chat_repository.RagChatRecord(
        chat_id=request.chat_id or answer.metadata.request_id or str(uuid4()),
        message_id=str(uuid4()),
        document_id=document_id,
        version_id=version_id,
        question=request.question,
        answer=answer.answer,
        audience=request.audience,
        no_data=answer.no_data,
        source_chunk_ids=[item.chunk_id for item in answer.source_fragments],
        llm_call_ids=answer.metadata.llm_call_ids,
        metadata={
            "provider": answer.metadata.analysis_provider,
            "model": answer.metadata.model_version,
            "prompt_version": answer.metadata.prompt_version,
        },
    )
    answer.metadata.rag_chat_saved = rag_chat_repository.save_rag_exchange(record)
    if not answer.metadata.rag_chat_saved:
        answer.metadata.warnings.append(
            "persistence warning: RAG exchange was not saved"
        )
    return answer


def _metadata(
    *,
    provider: str,
    model: str,
    selected_model: str,
    processing_mode: str,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
    warnings: list[str] | None = None,
    document_id: str | None = None,
    version_id: str | None = None,
    request_id: str | None = None,
    call_ids: list[str] | None = None,
    latency_ms: int | None = None,
) -> AnalysisMetadata:
    return AnalysisMetadata(
        analysis_provider=provider,
        model_version=model,
        prompt_version=RAG_PROMPT_VERSION,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        processing_mode=processing_mode,
        warnings=warnings or [],
        selected_model=selected_model,
        context_document_id=document_id,
        context_version_id=version_id,
        request_id=request_id,
        llm_call_ids=call_ids or [],
        latency_ms=latency_ms,
    )


def _extractive_fallback(top_fragments: list[RagSourceFragment]) -> str:
    excerpts = " ".join(fragment.text for fragment in top_fragments[:2])
    return (
        "На основании найденных фрагментов можно сделать предварительный "
        f"вывод: {excerpts}"
    )


def sanitize_rag_answer(
    answer: str,
    fragments: list[RagSourceFragment],
) -> str:
    """Keep source identifiers in citations, never in user-visible prose."""
    cleaned = re.sub(
        r"\b(?:document_id|version_id|chunk_id)\b\s*[:=]?\s*[\w.-]*",
        "",
        answer,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:chunk|source|evidence)[_-]\d+\b",
        "фрагмент источника",
        cleaned,
        flags=re.IGNORECASE,
    )
    identifiers = {
        identifier
        for fragment in fragments
        for identifier in (
            fragment.document_id,
            fragment.version_id,
            fragment.chunk_id,
        )
        if identifier and len(identifier) >= 2
    }
    for identifier in sorted(identifiers, key=len, reverse=True):
        cleaned = re.sub(
            re.escape(identifier),
            "фрагмент источника",
            cleaned,
            flags=re.IGNORECASE,
        )
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,;:-")
    return cleaned or "Вывод основан на фрагментах источника, приведённых ниже."


def ask_rag(request: RagAskRequest, endpoint: str | None = None) -> RagAnswer:
    config = get_config()
    selection = resolve_model_selection(request.model_override, config)
    request_id = request.request_id or str(uuid4())
    fragments = _request_fragments(request)
    top_fragments = retrieve_top_fragments(
        request.question,
        fragments,
        request.top_k,
    )
    notice = _safety_notice(request.audience)

    if not top_fragments:
        skipped_record = LLMCallLogRecord(
            request_id=request_id,
            endpoint=endpoint,
            operation="rag_answer",
            provider="none",
            runtime="NO_DATA",
            model=None,
            selected_model=selection.selected_model,
            prompt_version=RAG_PROMPT_VERSION,
            status="skipped",
            input_chars=len(request.question),
            input_tokens_estimate=estimate_tokens(len(request.question)),
            metadata={"reason": "no_source_fragments"},
        )
        log_llm_call(skipped_record)
        return _persist_rag_answer(request, RagAnswer(
            answer=NO_DATA_ANSWER,
            audience=request.audience,
            no_data=True,
            source_fragments=[],
            safety_notice=notice,
            metadata=_metadata(
                provider="none",
                model="none",
                selected_model=selection.selected_model,
                processing_mode="rag_no_data",
                document_id=request.document_id,
                version_id=request.version_id,
                request_id=request_id,
                call_ids=[skipped_record.call_id],
            ),
        ))

    serialized_fragments = [fragment.model_dump() for fragment in top_fragments]
    provider_name = "polza" if config.is_polza_mode else "mock"
    gateway: LLMGateway | None = None
    input_chars = len(request.question) + sum(
        len(fragment.text) for fragment in top_fragments
    )
    try:
        prompt = load_prompt(
            RAG_PROMPT_VERSION,
            {
                "audience": request.audience,
                "question": request.question,
                "source_fragments": json.dumps(
                    serialized_fragments,
                    ensure_ascii=False,
                    indent=2,
                ),
            },
        )
        gateway = LLMGateway()
        result = gateway.generate_structured(
            prompt=prompt,
            response_model=RagLLMOutput,
            metadata={
                "task": "rag_answer",
                "prompt_version": RAG_PROMPT_VERSION,
                "audience": request.audience,
                "rag_fragments": serialized_fragments,
                "request_id": request_id,
                "endpoint": endpoint,
                "operation": "rag_answer",
                "input_chars": input_chars,
                "selected_model": selection.selected_model,
            },
            model_override=selection.gateway_override,
        )
        output = RagLLMOutput.model_validate(result)
        if output.no_data:
            return _persist_rag_answer(request, RagAnswer(
                answer=NO_DATA_ANSWER,
                audience=request.audience,
                no_data=True,
                source_fragments=[],
                safety_notice=notice,
                metadata=_metadata(
                    provider=provider_name,
                    model=gateway.last_model,
                    selected_model=selection.selected_model,
                    processing_mode=f"rag_gateway_{provider_name}",
                    warnings=gateway.last_warnings,
                    document_id=request.document_id,
                    version_id=request.version_id,
                    request_id=request_id,
                    call_ids=list(gateway.last_call_ids),
                    latency_ms=gateway.last_latency_ms,
                ),
            ))
        used_ids = set(output.used_fragment_ids)
        cited = [
            fragment
            for fragment in top_fragments
            if fragment.chunk_id in used_ids
        ] or top_fragments
        return _persist_rag_answer(request, RagAnswer(
            answer=sanitize_rag_answer(output.answer, top_fragments),
            audience=request.audience,
            no_data=False,
            source_fragments=cited,
            safety_notice=notice,
            metadata=_metadata(
                provider=provider_name,
                model=gateway.last_model,
                selected_model=selection.selected_model,
                processing_mode=f"rag_gateway_{provider_name}",
                warnings=gateway.last_warnings,
                document_id=request.document_id,
                version_id=request.version_id,
                request_id=request_id,
                call_ids=list(gateway.last_call_ids),
                latency_ms=gateway.last_latency_ms,
            ),
        ))
    except RAG_FALLBACK_ERRORS as error:
        fallback_record = LLMCallLogRecord(
            request_id=request_id,
            endpoint=endpoint,
            operation="fallback",
            provider="mock",
            runtime="FALLBACK",
            model=DEFAULT_MODEL_VERSION,
            selected_model=selection.selected_model,
            prompt_version=RAG_PROMPT_VERSION,
            status="fallback",
            input_chars=input_chars,
            input_tokens_estimate=estimate_tokens(input_chars),
            fallback_used=True,
            fallback_reason=f"{type(error).__name__}: {error}",
            error_type=type(error).__name__,
            error_message=str(error),
            warnings=["LLM RAG failed; extractive fallback was used."],
            metadata={"reason": "rag_extractive_fallback"},
        )
        log_llm_call(fallback_record)
        gateway_call_ids = list(gateway.last_call_ids) if gateway else []
        return _persist_rag_answer(request, RagAnswer(
            answer=sanitize_rag_answer(
                _extractive_fallback(top_fragments),
                top_fragments,
            ),
            audience=request.audience,
            no_data=False,
            source_fragments=top_fragments,
            safety_notice=notice,
            metadata=_metadata(
                provider=provider_name,
                model=(selection.selected_model if config.is_polza_mode else DEFAULT_MODEL_VERSION),
                selected_model=selection.selected_model,
                processing_mode="rag_extractive_fallback",
                fallback_used=True,
                fallback_reason=f"{type(error).__name__}: {error}",
                warnings=["LLM RAG failed; extractive fallback was used."],
                document_id=request.document_id,
                version_id=request.version_id,
                request_id=request_id,
                call_ids=gateway_call_ids + [fallback_record.call_id],
                latency_ms=gateway.last_latency_ms if gateway else None,
            ),
        ))
