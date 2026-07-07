"""Provider-neutral structured generation gateway."""

import json
import logging
import re
import time
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from .base import LLMProvider, LLMRequest
from .config import get_config
from .errors import (
    LLMGatewayError,
    LLMProviderConfigError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMResponseParsingError,
    LLMResponseValidationError,
)
from .router import get_llm_provider
from ..llm_call_logger import (
    LLMCallLogRecord,
    estimate_tokens,
    log_llm_call,
    sanitize_log_text,
)

logger = logging.getLogger(__name__)


def extract_json_object(raw_text: str) -> tuple[dict, str | None]:
    """Extract a JSON object from clean, fenced, or prose-wrapped output."""
    stripped = raw_text.strip()
    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value, None
    except json.JSONDecodeError:
        pass

    fence = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        stripped,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fence:
        try:
            value = json.loads(fence.group(1))
            if isinstance(value, dict):
                return value, "JSON was extracted from a Markdown code fence."
        except json.JSONDecodeError:
            pass

    decoder = json.JSONDecoder()
    for index, character in enumerate(stripped):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value, "JSON was extracted from surrounding model text."

    raise LLMResponseParsingError(
        "Ответ провайдера не содержит валидный JSON object.",
        raw_text=raw_text,
    )


class LLMGateway:
    """Select a provider, retry failures, extract JSON and validate Pydantic."""

    def __init__(self) -> None:
        self._config = get_config()
        self._provider: LLMProvider = get_llm_provider(self._config)
        self.last_warnings: list[str] = []
        self.last_model: str = self._config.active_model
        self.last_call_ids: list[str] = []
        self.last_latency_ms: int | None = None
        self.last_request_id: str | None = None

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def generate_structured(
        self,
        prompt: str,
        response_model: type[BaseModel],
        metadata: dict | None = None,
        model_override: str | None = None,
    ) -> BaseModel:
        if not hasattr(self, "last_call_ids"):
            self.last_call_ids = []
        if not hasattr(self, "last_latency_ms"):
            self.last_latency_ms = None
        if not hasattr(self, "last_warnings"):
            self.last_warnings = []
        metadata = metadata or {}
        request_id = str(metadata.get("request_id") or uuid4())
        metadata = {**metadata, "request_id": request_id}
        self.last_request_id = request_id
        max_retries = self._config.active_max_retries
        self.last_warnings = []
        request_model = model_override or self._config.active_model
        self.last_model = request_model
        last_error: LLMGatewayError | None = None

        for attempt in range(max_retries + 1):
            start = time.perf_counter()
            try:
                raw_response = self._provider.complete(
                    LLMRequest(
                        prompt=prompt,
                        model=request_model,
                        metadata=metadata,
                    )
                )
                self.last_model = raw_response.model
                parsed, extraction_warning = extract_json_object(
                    raw_response.raw_text
                )
                if extraction_warning:
                    self.last_warnings.append(extraction_warning)
                result = response_model.model_validate(parsed)
            except LLMProviderConfigError as error:
                last_error = error
            except (TimeoutError, LLMProviderTimeoutError) as error:
                last_error = LLMProviderTimeoutError(
                    f"Таймаут LLM-провайдера '{self._provider.name}': {error}",
                    provider=self._provider.name,
                )
            except LLMProviderUnavailableError as error:
                last_error = error
            except LLMResponseParsingError as error:
                if error.provider is None:
                    error.provider = self._provider.name
                last_error = error
            except ValidationError as error:
                last_error = LLMResponseValidationError(
                    f"Ответ провайдера '{self._provider.name}' не соответствует "
                    f"схеме {response_model.__name__}: {error}",
                    raw_text=raw_response.raw_text,
                    provider=self._provider.name,
                )
            except Exception as error:
                last_error = LLMProviderUnavailableError(
                    f"Ошибка LLM-провайдера '{self._provider.name}': {error}",
                    provider=self._provider.name,
                )
            else:
                latency_ms = (time.perf_counter() - start) * 1000
                self._log_call(
                    provider=self._provider.name,
                    model=raw_response.model,
                    status="success",
                    latency_ms=latency_ms,
                    tokens_used=raw_response.tokens_used,
                    output_chars=len(raw_response.raw_text),
                    metadata=metadata,
                )
                return result

            latency_ms = (time.perf_counter() - start) * 1000
            error_status = (
                "timeout"
                if isinstance(last_error, LLMProviderTimeoutError)
                else "validation_error"
                if isinstance(
                    last_error,
                    (LLMResponseParsingError, LLMResponseValidationError),
                )
                else "error"
            )
            self._log_call(
                provider=self._provider.name,
                model=request_model,
                status=error_status,
                latency_ms=latency_ms,
                error=last_error,
                fallback_possible=True,
                metadata=metadata,
            )
            logger.warning(
                "LLM call attempt %s/%s failed: %s: %s",
                attempt + 1,
                max_retries + 1,
                type(last_error).__name__,
                last_error,
            )
            if isinstance(last_error, LLMProviderConfigError):
                break

        assert last_error is not None
        raise last_error

    def _log_call(
        self,
        provider: str,
        model: str,
        status: str,
        latency_ms: float,
        tokens_used: int | None = None,
        output_chars: int | None = None,
        error: Exception | None = None,
        fallback_possible: bool = False,
        metadata: dict | None = None,
    ) -> str:
        metadata = metadata or {}
        operation = str(
            metadata.get("operation")
            or metadata.get("task")
            or metadata.get("prompt_name")
            or "gateway_test"
        )
        if operation not in {
            "document_analysis",
            "rag_answer",
            "language_retry",
            "fallback",
            "mock",
            "gateway_test",
        }:
            operation = "gateway_test"
        input_chars = metadata.get("input_chars")
        input_chars = input_chars if isinstance(input_chars, int) else None
        sensitive_values = tuple(
            value
            for key, value in metadata.items()
            if isinstance(value, str)
            and key.casefold() in {"document_text", "prompt"}
        )
        safe_error = sanitize_log_text(error, sensitive_values)
        record = LLMCallLogRecord(
            request_id=str(metadata.get("request_id")) if metadata.get("request_id") else None,
            endpoint=str(metadata.get("endpoint")) if metadata.get("endpoint") else None,
            operation=operation,
            provider=provider,
            runtime="POLZA" if provider == "polza" else "MOCK",
            model=model,
            selected_model=(
                str(metadata.get("selected_model"))
                if metadata.get("selected_model")
                else model
            ),
            prompt_version=(
                str(metadata.get("prompt_version"))
                if metadata.get("prompt_version")
                else None
            ),
            status=status,
            latency_ms=round(latency_ms),
            input_chars=input_chars,
            output_chars=output_chars,
            input_tokens_estimate=estimate_tokens(input_chars),
            output_tokens_estimate=estimate_tokens(output_chars),
            error_type=type(error).__name__ if error else None,
            error_message=safe_error,
            warnings=list(self.last_warnings),
            metadata={
                "attempt": metadata.get("attempt"),
                "fallback_possible": fallback_possible,
                "provider_tokens_used": tokens_used,
                **metadata,
            },
        )
        log_llm_call(record)
        self.last_call_ids.append(record.call_id)
        self.last_latency_ms = (self.last_latency_ms or 0) + (record.latency_ms or 0)
        log = logger.info if status == "success" else logger.error
        log(
            "LLM call: provider=%s, model=%s, status=%s, error_type=%s, "
            "error=%s, latency_ms=%.1f, tokens=%s, fallback_possible=%s",
            record.provider,
            record.model,
            record.status,
            record.error_type,
            record.error_message,
            record.latency_ms,
            tokens_used,
            fallback_possible,
        )
        return record.call_id
