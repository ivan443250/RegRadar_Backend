class LLMGatewayError(Exception):
    """Базовая ошибка LLM Gateway."""

    def __init__(self, message: str, provider: str | None = None):
        self.provider = provider
        super().__init__(message)


class LLMProviderConfigError(LLMGatewayError):
    """Ошибка конфигурации или выбора LLM-провайдера."""


class LLMProviderUnavailableError(LLMGatewayError):
    """LLM-провайдер недоступен или завершил вызов с ошибкой."""


class LLMProviderTimeoutError(LLMProviderUnavailableError):
    """Истёк таймаут вызова LLM-провайдера."""


class JSONValidationError(LLMGatewayError):
    """Совместимая базовая ошибка JSON / Pydantic ответа."""

    def __init__(self, message: str, raw_text: str = "", provider: str | None = None):
        self.raw_text = raw_text[:500]
        super().__init__(message, provider=provider)


class LLMResponseParsingError(JSONValidationError):
    """Ответ LLM не является валидным JSON."""


class LLMResponseValidationError(JSONValidationError):
    """JSON-ответ LLM не соответствует ожидаемой Pydantic-схеме."""


class LLMResponseLanguageError(LLMGatewayError):
    """LLM returned non-Russian content in user-visible fields."""

    def __init__(self, warnings: list[str], provider: str = "polza"):
        self.warnings = warnings
        super().__init__(
            "LLM returned non-Russian user-visible fields",
            provider=provider,
        )


class ProviderNotFoundError(LLMProviderConfigError):
    """Провайдер не найден."""

    def __init__(self, provider_name: str):
        super().__init__(
            f"LLM-провайдер '{provider_name}' не найден. "
            f"Доступные провайдеры: mock, polza, polza_with_fallback. "
            f"Проверьте переменную окружения LLM_PROVIDER.",
            provider=provider_name,
        )


class ProviderNotConfiguredError(LLMProviderConfigError):
    """Провайдер не настроен (нет API-ключа и т.п.)."""

    def __init__(self, provider_name: str, detail: str = ""):
        msg = f"LLM-провайдер '{provider_name}' не настроен."
        if detail:
            msg += f" {detail}"
        super().__init__(msg, provider=provider_name)


class LLMCallError(LLMProviderUnavailableError):
    """Совместимая ошибка недоступности при вызове LLM."""

    def __init__(self, message: str, provider: str | None = None):
        super().__init__(message, provider=provider)
