from .base import LLMProvider
from .config import GatewayConfig
from .errors import ProviderNotFoundError
from .mock_provider import MockLLMProvider
from .polza_provider import PolzaAIProvider


def get_llm_provider(config: GatewayConfig) -> LLMProvider:
    """Выбрать LLM-провайдера на основе конфигурации.

    - LLM_PROVIDER=mock → MockLLMProvider (работает всегда)
    - LLM_PROVIDER=polza → PolzaAIProvider (требует API-ключ)
    - неизвестный → ProviderNotFoundError
    """
    provider_name = config.llm_provider.lower().strip()

    if provider_name == "mock":
        return MockLLMProvider()

    if provider_name in {"polza", "polza_with_fallback"}:
        return PolzaAIProvider(
            api_key=config.polzaai_api_key,
            base_url=config.polzaai_base_url,
            timeout_seconds=config.polza_timeout_seconds,
        )

    raise ProviderNotFoundError(config.llm_provider)
