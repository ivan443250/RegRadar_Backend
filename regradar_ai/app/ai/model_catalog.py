"""Backend-owned model allowlist and public model catalog."""

from dataclasses import dataclass

from .gateway.config import GatewayConfig


MODEL_PRESENTATION: dict[str, tuple[str, str]] = {
    "deepseek/deepseek-v4-flash": (
        "DeepSeek V4 Flash",
        "Дешёвая быстрая модель для массовой обработки документов",
    ),
    "openai/gpt-4o": (
        "GPT-4o",
        "Более сильная модель для финального демо и сложных документов",
    ),
    "qwen/qwen3.6-plus": (
        "Qwen 3.6 Plus",
        "Компромисс цена/качество",
    ),
    "qwen/qwen3.5-flash-02-23": (
        "Qwen 3.5 Flash",
        "Очень дешёвый вариант для массовых прогонов",
    ),
}


class ModelNotAllowedError(ValueError):
    def __init__(self, model: str, allowed_models: tuple[str, ...]):
        self.model = model
        self.allowed_models = allowed_models
        super().__init__(
            f"Model '{model}' is not allowed. Allowed models: "
            f"{', '.join(allowed_models)}"
        )


@dataclass(frozen=True)
class ModelSelection:
    selected_model: str
    gateway_override: str | None


def resolve_model_selection(
    model_override: str | None,
    config: GatewayConfig,
) -> ModelSelection:
    requested = model_override.strip() if model_override else None
    if config.is_polza_mode:
        if requested and requested not in config.polza_allowed_models:
            raise ModelNotAllowedError(requested, config.polza_allowed_models)
        selected = requested or config.polza_model
        return ModelSelection(selected_model=selected, gateway_override=requested)

    # Mock never sends the frontend choice to an external provider.
    return ModelSelection(
        selected_model=requested or config.active_model,
        gateway_override=None,
    )


def public_model_catalog(config: GatewayConfig) -> list[dict[str, str]]:
    catalog: list[dict[str, str]] = []
    for model_id in config.polza_allowed_models:
        label, description = MODEL_PRESENTATION.get(
            model_id,
            (model_id, "Модель разрешена конфигурацией backend"),
        )
        catalog.append(
            {"id": model_id, "label": label, "description": description}
        )
    return catalog
