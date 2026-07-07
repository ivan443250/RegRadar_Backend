from datetime import datetime, timezone
from typing import Annotated, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field, StringConstraints


LLMCallStatus = Literal["success", "error"]
NonEmptyPrompt = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


# --- Request / Response models ---

class LLMRequest(BaseModel):
    """Универсальный запрос к LLM-провайдеру."""

    prompt: NonEmptyPrompt
    model: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.0
    metadata: dict = Field(default_factory=dict)


class LLMRawResponse(BaseModel):
    """Сырой ответ от LLM-провайдера."""

    raw_text: str
    model: str
    provider: str
    tokens_used: int | None = None
    latency_ms: float = 0.0
    finish_reason: str | None = None
    metadata: dict = Field(default_factory=dict)


class LLMCallLogRecord(BaseModel):
    """Запись лога вызова LLM."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provider: str
    model: str
    status: LLMCallStatus
    latency_ms: float = Field(ge=0.0)
    tokens_used: int | None = None
    error_type: str | None = None
    error: str | None = None
    error_message: str | None = None
    fallback_possible: bool = False
    request_metadata: dict = Field(default_factory=dict)


# --- Provider Protocol ---

@runtime_checkable
class LLMProvider(Protocol):
    """Абстрактный интерфейс LLM-провайдера.

    Все провайдеры должны реализовать:
    - name: str — имя провайдера
    - complete(request: LLMRequest) -> LLMRawResponse
    """

    name: str

    def complete(self, request: LLMRequest) -> LLMRawResponse:
        ...
