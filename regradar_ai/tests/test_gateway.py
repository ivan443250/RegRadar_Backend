"""Unit-тесты для LLM Gateway: mock provider, ошибки, retry, config."""


import json

import httpx
import pytest
from pydantic import BaseModel

from app.ai.gateway.base import LLMRequest, LLMRawResponse
from app.ai.gateway.config import GatewayConfig, reset_config
from app.ai.gateway.errors import (
    JSONValidationError,
    LLMCallError,
    LLMProviderConfigError,
    LLMProviderTimeoutError,
    LLMResponseParsingError,
    LLMResponseValidationError,
    ProviderNotFoundError,
    ProviderNotConfiguredError,
)
from app.ai.gateway.gateway import LLMGateway
from app.ai.gateway.mock_provider import MockLLMProvider
from app.ai.gateway.polza_provider import PolzaAIProvider
from app.ai.gateway.router import get_llm_provider
from app.ai.schemas import DocumentAnalysis


# --- MockLLMProvider ---


def test_mock_provider_returns_valid_json():
    """MockLLMProvider возвращает JSON, проходящий Pydantic-валидацию."""
    provider = MockLLMProvider()
    request = LLMRequest(
        prompt="Анализируйте документ о персональных данных.",
        model="mock-reg-radar-v1",
        metadata={"document_text": "Требования 152-ФЗ по обработке персональных данных."},
    )
    response = provider.complete(request)
    assert isinstance(response, LLMRawResponse)
    assert response.provider == "mock"
    assert response.raw_text

    import json
    parsed = json.loads(response.raw_text)
    doc = DocumentAnalysis.model_validate(parsed)
    assert doc.title
    assert doc.short_summary
    assert isinstance(doc.topics, list)


def test_mock_provider_name():
    provider = MockLLMProvider()
    assert provider.name == "mock"


def test_mock_provider_latency_positive():
    provider = MockLLMProvider()
    request = LLMRequest(prompt="Тест", model="mock-reg-radar-v1")
    response = provider.complete(request)
    assert response.latency_ms >= 0


# --- Router ---


def test_router_returns_mock_for_mock_config():
    config = GatewayConfig(llm_provider="mock")
    provider = get_llm_provider(config)
    assert isinstance(provider, MockLLMProvider)


def test_router_returns_polza_for_polza_config():
    config = GatewayConfig(llm_provider="polza", polzaai_api_key="test-key")
    provider = get_llm_provider(config)
    assert isinstance(provider, PolzaAIProvider)


def test_router_raises_for_unknown_provider():
    config = GatewayConfig(llm_provider="unknown_provider")
    with pytest.raises(ProviderNotFoundError) as exc_info:
        get_llm_provider(config)
    assert isinstance(exc_info.value, LLMProviderConfigError)
    assert "unknown_provider" in str(exc_info.value)


def test_router_case_insensitive():
    config = GatewayConfig(llm_provider="MOCK")
    provider = get_llm_provider(config)
    assert isinstance(provider, MockLLMProvider)


# --- PolzaAIProvider (skeleton) ---


def test_polza_raises_without_api_key():
    provider = PolzaAIProvider(api_key=None)
    request = LLMRequest(prompt="Тест", model="test")
    with pytest.raises(ProviderNotConfiguredError):
        provider.complete(request)


def test_polza_with_key_uses_mocked_openai_compatible_http():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://polza.test/api/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer fake-key"
        payload = json.loads(request.content)
        assert payload["model"] == "test"
        assert [message["role"] for message in payload["messages"]] == [
            "system",
            "user",
        ]
        return httpx.Response(
            200,
            json={
                "model": "test",
                "choices": [
                    {
                        "message": {"content": '{"title":"ok"}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"total_tokens": 7},
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = PolzaAIProvider(
        api_key="fake-key",
        base_url="https://polza.test/api/v1",
        client=http_client,
    )
    request = LLMRequest(prompt="Тест", model="test")
    response = provider.complete(request)
    http_client.close()

    assert response.raw_text == '{"title":"ok"}'
    assert response.provider == "polza"
    assert response.tokens_used == 7


# --- Errors ---


def test_provider_not_found_error_contains_provider_name():
    err = ProviderNotFoundError("foobar")
    assert "foobar" in str(err)
    assert err.provider == "foobar"


def test_json_validation_error_has_raw_text():
    err = JSONValidationError("bad json", raw_text="{broken", provider="mock")
    assert err.raw_text == "{broken"
    assert err.provider == "mock"


def test_llm_call_error_has_provider():
    err = LLMCallError("connection failed", provider="polza")
    assert err.provider == "polza"


# --- LLMGateway ---


def test_gateway_generate_structured_returns_document_analysis():
    """Gateway с mock-провайдером возвращает валидный DocumentAnalysis."""
    gateway = LLMGateway()
    result = gateway.generate_structured(
        prompt="Требования 152-ФЗ по обработке персональных данных.",
        response_model=DocumentAnalysis,
        metadata={"document_text": "Требования 152-ФЗ по обработке персональных данных."},
    )
    assert isinstance(result, DocumentAnalysis)
    assert result.title
    assert result.short_summary


def test_gateway_provider_name_is_mock():
    gateway = LLMGateway()
    assert gateway.provider_name == "mock"


# --- Gateway validation errors ---


def test_gateway_rejects_invalid_json_from_provider(monkeypatch):
    """Если provider возвращает невалидный JSON, Gateway бросает JSONValidationError."""

    class BrokenProvider:
        name = "broken"

        def complete(self, request: LLMRequest) -> LLMRawResponse:
            return LLMRawResponse(
                raw_text="this is not json",
                model="broken-v1",
                provider="broken",
            )

    gateway = LLMGateway.__new__(LLMGateway)
    from app.ai.gateway.config import GatewayConfig
    gateway._config = GatewayConfig()
    gateway._provider = BrokenProvider()

    with pytest.raises(LLMResponseParsingError):
        gateway.generate_structured(
            prompt="тест",
            response_model=DocumentAnalysis,
        )


def test_gateway_rejects_schema_mismatch(monkeypatch):
    """Если JSON валидный, но не соответствует схеме, Gateway бросает JSONValidationError."""
    import json as json_mod

    class WrongSchemaProvider:
        name = "wrong"

        def complete(self, request: LLMRequest) -> LLMRawResponse:
            return LLMRawResponse(
                raw_text=json_mod.dumps({"unrelated_field": 42}),
                model="wrong-v1",
                provider="wrong",
            )

    gateway = LLMGateway.__new__(LLMGateway)
    from app.ai.gateway.config import GatewayConfig
    gateway._config = GatewayConfig()
    gateway._provider = WrongSchemaProvider()

    with pytest.raises(LLMResponseValidationError):
        gateway.generate_structured(
            prompt="тест",
            response_model=DocumentAnalysis,
        )


def test_gateway_types_provider_timeout_and_logs_observability(caplog):
    class TimeoutProvider:
        name = "timeout-provider"

        def complete(self, request: LLMRequest) -> LLMRawResponse:
            raise TimeoutError("deadline exceeded")

    gateway = LLMGateway.__new__(LLMGateway)
    gateway._config = GatewayConfig(llm_max_retries=0)
    gateway._provider = TimeoutProvider()

    with caplog.at_level("ERROR", logger="app.ai.gateway.gateway"):
        with pytest.raises(LLMProviderTimeoutError):
            gateway.generate_structured(
                prompt="тест",
                response_model=DocumentAnalysis,
            )

    assert "error_type=LLMProviderTimeoutError" in caplog.text
    assert "fallback_possible=True" in caplog.text


# --- Config ---


def test_config_defaults():
    reset_config()
    config = GatewayConfig()
    assert config.llm_provider == "mock"
    assert config.llm_model == "mock-reg-radar-v1"
    assert config.llm_max_retries == 2
    assert config.llm_timeout_seconds == 30


def test_config_reads_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza")
    monkeypatch.setenv("LLM_MODEL", "custom-model")
    monkeypatch.setenv("LLM_MAX_RETRIES", "5")
    config = GatewayConfig()
    assert config.llm_provider == "polza"
    assert config.llm_model == "custom-model"
    assert config.llm_max_retries == 5


def test_config_reads_polza_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "polza_with_fallback")
    monkeypatch.setenv("POLZA_API_KEY", "secret")
    monkeypatch.setenv("POLZA_BASE_URL", "https://polza.test/v1")
    monkeypatch.setenv("POLZA_MODEL", "provider/model")
    monkeypatch.setenv("POLZA_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("POLZA_MAX_RETRIES", "4")

    config = GatewayConfig()

    assert config.polzaai_api_key == "secret"
    assert config.polzaai_base_url == "https://polza.test/v1"
    assert config.active_model == "provider/model"
    assert config.active_timeout_seconds == 45
    assert config.active_max_retries == 4
