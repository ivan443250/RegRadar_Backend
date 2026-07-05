import re
from dataclasses import dataclass


@dataclass
class AnalysisResult:
    title: str
    summary: str
    category: str
    impact: str
    impact_reason: str


RULES: list[dict] = [
    {
        "keywords": ["персональные данные", "152-фз"],
        "category": "персональные данные",
        "impact": "high",
        "reason": "Затрагивает обработку персональных данных (152-ФЗ).",
    },
    {
        "keywords": ["115-фз", "под/фт", "идентификация"],
        "category": "115-ФЗ",
        "impact": "high",
        "reason": "Затрагивает требования ПОД/ФТ (115-ФЗ).",
    },
    {
        "keywords": ["вэд", "импорт", "экспорт"],
        "category": "ВЭД",
        "impact": "medium",
        "reason": "Затрагивает внешнеэкономическую деятельность.",
    },
]

DEFAULT_CATEGORY = "общее регулирование"
DEFAULT_IMPACT = "low"
DEFAULT_REASON = "Нет явных триггеров для специализированных категорий."


def _first_sentence(text: str) -> str:
    """Извлечь первое предложение как заголовок."""
    match = re.match(r"(.+?[.!?])\s", text)
    return match.group(1) if match else text[:200]


def analyze(text: str) -> AnalysisResult:
    """Rule-based анализ регуляторного текста.

    Проверяет текст на ключевые слова из RULES по порядку —
    первое совпадение определяет категорию и impact.
    """
    lower = text.lower()

    category = DEFAULT_CATEGORY
    impact = DEFAULT_IMPACT
    reason = DEFAULT_REASON

    for rule in RULES:
        if any(kw in lower for kw in rule["keywords"]):
            category = rule["category"]
            impact = rule["impact"]
            reason = rule["reason"]
            break

    title = _first_sentence(text)
    summary = text[:300] + ("..." if len(text) > 300 else "")

    return AnalysisResult(
        title=title,
        summary=summary,
        category=category,
        impact=impact,
        impact_reason=reason,
    )
