"""PolzaAI OpenAI-compatible Chat Completions provider."""

import time
from typing import Any

import httpx

from .base import LLMRequest, LLMRawResponse
from .errors import (
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    ProviderNotConfiguredError,
)


SYSTEM_MESSAGE = (
    "You extract structured facts from regulatory documents. "
    "Return only one valid JSON object without Markdown or commentary. "
    "Never provide legal advice."
)


class PolzaAIProvider:
    """Synchronous HTTP adapter for PolzaAI's OpenAI-compatible endpoint."""

    name = "polza"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 60,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key.strip() if api_key else None
        self._base_url = (base_url or "https://polza.ai/api/v1").rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client

    def complete(self, request: LLMRequest) -> LLMRawResponse:
        if not self._api_key:
            raise ProviderNotConfiguredError(
                self.name,
                detail=(
                    "POLZA_API_KEY не задан. Будет использован безопасный "
                    "MockProvider fallback."
                ),
            )

        messages = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": request.prompt},
        ]
        language_correction = request.metadata.get("additional_user_message")
        if language_correction:
            messages.append(
                {"role": "user", "content": str(language_correction)}
            )

        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        start = time.perf_counter()

        try:
            if self._client is not None:
                response = self._client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(
                        f"{self._base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            choice = body["choices"][0]
            raw_text = choice["message"]["content"]
            if not isinstance(raw_text, str) or not raw_text.strip():
                raise ValueError("Empty choices[0].message.content")
        except httpx.TimeoutException as error:
            raise LLMProviderTimeoutError(
                f"PolzaAI request timed out after {self._timeout_seconds}s: {error}",
                provider=self.name,
            ) from error
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            raise LLMProviderUnavailableError(
                f"PolzaAI HTTP {status}: {error.response.text[:300]}",
                provider=self.name,
            ) from error
        except (httpx.RequestError, ValueError, KeyError, IndexError, TypeError) as error:
            raise LLMProviderUnavailableError(
                f"Invalid or unavailable PolzaAI response: {error}",
                provider=self.name,
            ) from error

        usage = body.get("usage") or {}
        return LLMRawResponse(
            raw_text=raw_text,
            model=str(body.get("model") or request.model or "unknown"),
            provider=self.name,
            tokens_used=usage.get("total_tokens"),
            latency_ms=(time.perf_counter() - start) * 1000,
            finish_reason=choice.get("finish_reason"),
            metadata=request.metadata,
        )
