"""Manual PolzaAI connectivity smoke test. Never imported by pytest."""

from app.ai.gateway.base import LLMRequest
from app.ai.gateway.config import GatewayConfig
from app.ai.gateway.polza_provider import PolzaAIProvider


def main() -> int:
    config = GatewayConfig(llm_provider="polza")
    if not config.polzaai_api_key:
        print("POLZA_API_KEY is not configured; no request was sent.")
        return 0

    provider = PolzaAIProvider(
        api_key=config.polzaai_api_key,
        base_url=config.polzaai_base_url,
        timeout_seconds=config.polza_timeout_seconds,
    )
    try:
        response = provider.complete(
            LLMRequest(
                prompt='Return only this JSON object: {"status":"ok"}',
                model=config.polza_model,
                max_tokens=50,
            )
        )
    except Exception as error:
        print(f"PolzaAI connection failed: {type(error).__name__}: {error}")
        return 1

    print(
        f"PolzaAI connection OK: provider={response.provider} "
        f"model={response.model} status=success"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
