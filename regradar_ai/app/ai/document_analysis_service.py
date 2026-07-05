"""DocumentAnalysis through Gateway with controlled baseline reconciliation."""

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import uuid4

from .constants import DEFAULT_PROMPT_VERSION
from .domain_rules import (
    NEUTRAL_DOMAIN,
    NEUTRAL_TOPICS,
    SUPPORTED_DOMAINS,
    detect_domain,
)
from .gateway.gateway import LLMGateway
from .gateway.errors import (
    LLMProviderConfigError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMResponseParsingError,
    LLMResponseLanguageError,
    LLMResponseValidationError,
)
from .mock_provider import analyze_document as analyze_document_baseline
from .gateway.config import get_config
from .model_catalog import resolve_model_selection
from .language_guard import validate_document_analysis_language
from .prompt_loader import PromptNotFoundError, PromptRenderError, load_prompt
from .schemas import DocumentAnalysis
from .llm_call_logger import LLMCallLogRecord, estimate_tokens, log_llm_call
from .constants import DEFAULT_MODEL_VERSION


@dataclass(frozen=True)
class GatewayExecutionDetails:
    provider: str
    model: str
    warnings: tuple[str, ...] = ()
    request_id: str | None = None
    call_ids: tuple[str, ...] = ()
    latency_ms: int | None = None


_LAST_EXECUTION: ContextVar[GatewayExecutionDetails | None] = ContextVar(
    "document_analysis_gateway_execution",
    default=None,
)


def reset_last_gateway_execution() -> None:
    _LAST_EXECUTION.set(None)


def get_last_gateway_execution() -> GatewayExecutionDetails | None:
    return _LAST_EXECUTION.get()


def _verbatim_items(items: list[str], source_text: str) -> list[str]:
    return list(dict.fromkeys(item for item in items if item and item in source_text))


def reconcile_with_controlled_baseline(
    analysis: DocumentAnalysis,
    source_text: str,
) -> DocumentAnalysis:
    """Keep LLM extraction, but enforce safe domain routing and verbatim facts."""
    baseline = analyze_document_baseline(source_text)
    domain_rule = detect_domain(source_text)
    source_fragments = _verbatim_items(analysis.source_fragments, source_text)

    return analysis.model_copy(
        update={
            "domain": domain_rule.domain if domain_rule else NEUTRAL_DOMAIN,
            "topics": list(domain_rule.topics if domain_rule else NEUTRAL_TOPICS),
            "source_fragments": source_fragments or baseline.source_fragments,
            "obligations": _verbatim_items(analysis.obligations, source_text),
            "restrictions": _verbatim_items(analysis.restrictions, source_text),
            "penalties_or_consequences": _verbatim_items(
                analysis.penalties_or_consequences,
                source_text,
            ),
        }
    )


def analyze_document_with_gateway(
    text: str,
    model_override: str | None = None,
    request_id: str | None = None,
    endpoint: str | None = None,
) -> DocumentAnalysis:
    """Use an LLM only for DocumentAnalysis, then enforce baseline safety."""
    prompt = load_prompt(
        DEFAULT_PROMPT_VERSION,
        {
            "text": text,
            "supported_domains": ", ".join(SUPPORTED_DOMAINS),
        },
    )
    gateway = LLMGateway()
    selection = resolve_model_selection(model_override, get_config())
    effective_request_id = request_id or str(uuid4())
    request_metadata = {
        "request_id": effective_request_id,
        "endpoint": endpoint,
        "operation": "document_analysis",
        "prompt_name": "document_analysis",
        "prompt_version": DEFAULT_PROMPT_VERSION,
        "document_text": text,
        "input_chars": len(text),
        "selected_model": selection.selected_model,
    }
    try:
        result = gateway.generate_structured(
            prompt=prompt,
            response_model=DocumentAnalysis,
            metadata=request_metadata,
            model_override=selection.gateway_override,
        )
    except Exception:
        _LAST_EXECUTION.set(
            GatewayExecutionDetails(
                provider=gateway.provider_name,
                model=gateway.last_model,
                warnings=tuple(gateway.last_warnings),
                request_id=effective_request_id,
                call_ids=tuple(gateway.last_call_ids),
                latency_ms=gateway.last_latency_ms,
            )
        )
        raise
    document_analysis = DocumentAnalysis.model_validate(result)
    language_warnings = (
        validate_document_analysis_language(document_analysis)
        if gateway.provider_name == "polza"
        else []
    )

    if language_warnings:
        retry_metadata = {
            **request_metadata,
            "operation": "language_retry",
            "additional_user_message": (
                "Предыдущий ответ содержит английский текст. Верни тот же "
                "JSON строго на русском языке. source_fragments оставь "
                "дословными."
            ),
        }
        try:
            retry_result = gateway.generate_structured(
                prompt=prompt,
                response_model=DocumentAnalysis,
                metadata=retry_metadata,
                model_override=selection.gateway_override,
            )
        except Exception:
            _LAST_EXECUTION.set(
                GatewayExecutionDetails(
                    provider=gateway.provider_name,
                    model=gateway.last_model,
                    warnings=tuple(gateway.last_warnings),
                    request_id=effective_request_id,
                    call_ids=tuple(gateway.last_call_ids),
                    latency_ms=gateway.last_latency_ms,
                )
            )
            raise
        document_analysis = DocumentAnalysis.model_validate(retry_result)
        retry_language_warnings = validate_document_analysis_language(
            document_analysis
        )
        if retry_language_warnings:
            _LAST_EXECUTION.set(
                GatewayExecutionDetails(
                    provider=gateway.provider_name,
                    model=gateway.last_model,
                    warnings=tuple(
                        ["LLM language retry was used"]
                        + retry_language_warnings
                    ),
                    request_id=effective_request_id,
                    call_ids=tuple(gateway.last_call_ids),
                    latency_ms=gateway.last_latency_ms,
                )
            )
            raise LLMResponseLanguageError(retry_language_warnings)
        gateway.last_warnings.append("LLM language retry was used")

    _LAST_EXECUTION.set(
        GatewayExecutionDetails(
            provider=gateway.provider_name,
            model=gateway.last_model,
            warnings=tuple(gateway.last_warnings),
            request_id=effective_request_id,
            call_ids=tuple(gateway.last_call_ids),
            latency_ms=gateway.last_latency_ms,
        )
    )
    return reconcile_with_controlled_baseline(
        document_analysis,
        text,
    )


def analyze_document_with_safe_fallback(
    text: str,
    model_override: str | None = None,
    request_id: str | None = None,
    endpoint: str | None = None,
) -> DocumentAnalysis:
    """Gateway analysis for endpoints without metadata, always safely usable."""
    effective_request_id = request_id or str(uuid4())
    try:
        return analyze_document_with_gateway(
            text,
            model_override,
            request_id=effective_request_id,
            endpoint=endpoint,
        )
    except (
        LLMProviderConfigError,
        LLMProviderUnavailableError,
        LLMProviderTimeoutError,
        LLMResponseParsingError,
        LLMResponseLanguageError,
        LLMResponseValidationError,
        PromptNotFoundError,
        PromptRenderError,
    ) as error:
        config = get_config()
        selection = resolve_model_selection(model_override, config)
        fallback_record = LLMCallLogRecord(
            request_id=effective_request_id,
            endpoint=endpoint,
            operation="fallback",
            provider="mock",
            runtime="FALLBACK",
            model=DEFAULT_MODEL_VERSION,
            selected_model=selection.selected_model,
            prompt_version=DEFAULT_PROMPT_VERSION,
            status="fallback",
            input_chars=len(text),
            input_tokens_estimate=estimate_tokens(len(text)),
            fallback_used=True,
            fallback_reason=f"{type(error).__name__}: {error}",
            error_type=type(error).__name__,
            error_message=str(error),
            metadata={"reason": "safe_document_analysis_fallback"},
        )
        log_llm_call(fallback_record)
        return analyze_document_baseline(text)
