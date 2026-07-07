import os
from dataclasses import dataclass, field

from ..constants import DEFAULT_ANALYSIS_PROVIDER, DEFAULT_MODEL_VERSION


DEFAULT_POLZA_BASE_URL = "https://polza.ai/api/v1"
DEFAULT_POLZA_MODEL = "openai/gpt-4o"
DEFAULT_POLZA_ALLOWED_MODELS = (
    "deepseek/deepseek-v4-flash",
    "openai/gpt-4o",
    "qwen/qwen3.6-plus",
    "qwen/qwen3.5-flash-02-23",
)


def _allowed_models_from_env() -> tuple[str, ...]:
    raw_value = os.getenv("POLZA_ALLOWED_MODELS")
    if not raw_value:
        return DEFAULT_POLZA_ALLOWED_MODELS
    return tuple(
        dict.fromkeys(
            model.strip() for model in raw_value.split(",") if model.strip()
        )
    ) or DEFAULT_POLZA_ALLOWED_MODELS


@dataclass
class GatewayConfig:
    """Конфигурация LLM Gateway.

    Все значения читаются из переменных окружения с fallback-значениями.
    .env-файл не обязателен.
    """

    llm_provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", DEFAULT_ANALYSIS_PROVIDER)
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", DEFAULT_MODEL_VERSION)
    )
    llm_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    )
    llm_max_retries: int = field(
        default_factory=lambda: int(os.getenv("LLM_MAX_RETRIES", "2"))
    )
    polzaai_api_key: str | None = field(
        default_factory=lambda: os.getenv("POLZA_API_KEY")
        or os.getenv("POLZAAI_API_KEY")
    )
    polzaai_base_url: str | None = field(
        default_factory=lambda: os.getenv("POLZA_BASE_URL")
        or os.getenv("POLZAAI_BASE_URL")
        or DEFAULT_POLZA_BASE_URL
    )
    polza_model: str = field(
        default_factory=lambda: os.getenv("POLZA_MODEL", DEFAULT_POLZA_MODEL)
    )
    polza_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("POLZA_TIMEOUT_SECONDS", "60"))
    )
    polza_max_retries: int = field(
        default_factory=lambda: int(os.getenv("POLZA_MAX_RETRIES", "2"))
    )
    polza_allowed_models: tuple[str, ...] = field(
        default_factory=_allowed_models_from_env
    )

    @property
    def is_polza_mode(self) -> bool:
        return self.llm_provider.casefold().strip() in {
            "polza",
            "polza_with_fallback",
        }

    @property
    def active_model(self) -> str:
        return self.polza_model if self.is_polza_mode else self.llm_model

    @property
    def active_timeout_seconds(self) -> int:
        return (
            self.polza_timeout_seconds
            if self.is_polza_mode
            else self.llm_timeout_seconds
        )

    @property
    def active_max_retries(self) -> int:
        return self.polza_max_retries if self.is_polza_mode else self.llm_max_retries


# Глобальный экземпляр конфигурации (синглтон)
_config: GatewayConfig | None = None


def get_config() -> GatewayConfig:
    """Получить (или создать) конфигурацию gateway."""
    global _config
    if _config is None:
        _config = GatewayConfig()
    return _config


def reset_config() -> None:
    """Сбросить кеш конфигурации (для тестов)."""
    global _config
    _config = None
