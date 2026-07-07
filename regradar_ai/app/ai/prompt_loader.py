import re
from pathlib import Path
from string import Template
from typing import Mapping


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_NAME_PATTERN = re.compile(r"^[a-z0-9_-]+(?:\.md)?$")


class PromptNotFoundError(FileNotFoundError):
    """Запрошенный prompt отсутствует или имеет недопустимое имя."""


class PromptRenderError(ValueError):
    """Для рендеринга prompt не передана обязательная переменная."""


def load_prompt(
    name: str,
    variables: Mapping[str, object] | None = None,
) -> str:
    """Загрузить prompt по имени и безопасно подставить `${variable}`."""
    if not PROMPT_NAME_PATTERN.fullmatch(name):
        raise PromptNotFoundError(
            f"Prompt '{name}' не найден: допустимо только простое имя файла."
        )

    filename = name if name.endswith(".md") else f"{name}.md"
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.is_file():
        raise PromptNotFoundError(
            f"Prompt '{name}' не найден в каталоге '{PROMPTS_DIR}'."
        )

    template = Template(prompt_path.read_text(encoding="utf-8"))
    values = {key: str(value) for key, value in (variables or {}).items()}
    try:
        return template.substitute(values)
    except KeyError as error:
        missing_variable = error.args[0]
        raise PromptRenderError(
            f"Для prompt '{name}' не передана переменная '{missing_variable}'."
        ) from error
