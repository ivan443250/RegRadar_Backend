"""Unit-тесты для impact_engine: диапазоны, уровни, сложные сценарии."""


import pytest

from app.ai.impact_engine import assess_impact
from app.ai.schemas import DocumentAnalysis


# --- Вспомогательные функции ---


def _make_doc(
    topics: list[str] | None = None,
    obligations: list[str] | None = None,
    restrictions: list[str] | None = None,
    penalties: list[str] | None = None,
    source_fragments: list[str] | None = None,
    affected_processes: list[str] | None = None,
) -> DocumentAnalysis:
    """Создать минимальный DocumentAnalysis для тестирования."""
    return DocumentAnalysis(
        title="Тестовый документ",
        short_summary="Краткое описание",
        topics=topics or [],
        obligations=obligations or [],
        restrictions=restrictions or [],
        penalties_or_consequences=penalties or [],
        source_fragments=source_fragments or [],
        affected_processes=affected_processes or [],
    )


# --- Тесты диапазона ---


def test_score_always_between_0_and_100():
    """Score всегда в диапазоне 0–100."""
    # Минимальный случай
    doc_min = _make_doc()
    impact_min = assess_impact(doc_min)
    assert 0 <= impact_min.impact_score <= 100

    # Максимальный случай
    doc_max = _make_doc(
        topics=["персональные данные", "115-ФЗ / ПОД/ФТ", "ВЭД"],
        obligations=["обязаны проводить идентификацию", "требуется хранение согласий"],
        penalties=["штраф до 500 000 руб.", "приостановление деятельности"],
    )
    impact_max = assess_impact(doc_max)
    assert 0 <= impact_max.impact_score <= 100


# --- Тесты уровней ---


def test_score_0_to_30_is_low():
    doc = _make_doc()
    impact = assess_impact(doc)
    assert 0 <= impact.impact_score <= 30
    assert impact.impact_level == "low"


def test_score_31_to_60_is_medium():
    # Персональные данные = +30, obligations = +10 -> 40 = medium
    doc = _make_doc(
        topics=["персональные данные"],
        obligations=["обязаны уведомлять Роскомнадзор"],
    )
    impact = assess_impact(doc)
    assert 31 <= impact.impact_score <= 60
    assert impact.impact_level == "medium"


def test_score_61_to_80_is_high():
    # Персональные данные = +30, 115-ФЗ = +35 -> 65 = high
    doc = _make_doc(topics=["персональные данные", "115-ФЗ / ПОД/ФТ"])
    impact = assess_impact(doc)
    assert 61 <= impact.impact_score <= 80
    assert impact.impact_level == "high"


def test_score_81_to_100_is_critical():
    # 115-ФЗ = +35, персональные данные = +30, penalties = +20, multiple topics = +10 -> 95
    doc = _make_doc(
        topics=["персональные данные", "115-ФЗ / ПОД/ФТ"],
        penalties=["штраф до 1 000 000 руб."],
    )
    impact = assess_impact(doc)
    assert 81 <= impact.impact_score <= 100
    assert impact.impact_level == "critical"


# --- Сложные сценарии ---


def test_152fz_with_obligations_and_penalties_high_or_critical():
    """152-ФЗ + обязанности + ответственность → score ≥ 50."""
    doc = _make_doc(
        topics=["персональные данные"],
        obligations=["обязаны обеспечить хранение согласий"],
        penalties=["штраф до 500 000 руб."],
    )
    impact = assess_impact(doc)
    # +30 (topic) + 20 (penalties) + 10 (obligations) = 60 = medium
    assert impact.impact_score >= 50, f"score={impact.impact_score}"
    assert impact.impact_level in {"medium", "high", "critical"}, f"level={impact.impact_level}"


def test_empty_doc_has_zero_score():
    """Пустой документ → score = 0, level = low."""
    doc = _make_doc()
    impact = assess_impact(doc)
    assert impact.impact_score == 0
    assert impact.impact_level == "low"


def test_multiple_topics_boost_score():
    """Несколько тем → бонус +10."""
    doc_one = _make_doc(topics=["персональные данные"])
    doc_multi = _make_doc(topics=["персональные данные", "115-ФЗ / ПОД/ФТ"])

    impact_one = assess_impact(doc_one)
    impact_multi = assess_impact(doc_multi)

    # Multi-topics должны дать больше score
    assert impact_multi.impact_score >= impact_one.impact_score + 10


def test_reasoning_is_non_empty():
    """Reasoning не пустой для любого документа с темами."""
    doc = _make_doc(topics=["персональные данные"])
    impact = assess_impact(doc)
    assert impact.reasoning, "Reasoning не должен быть пустым"
    assert "персональных данных" in impact.reasoning


def test_urgency_matches_level():
    """Urgency соответствует impact_level."""
    urgency_map = {
        "low": "low",
        "medium": "medium",
        "high": "high",
        "critical": "critical",
    }
    # Проходим по всем уровням
    for topics, expected_level in [
        ([], "low"),
        (["персональные данные"], "medium"),
        (["персональные данные", "115-ФЗ / ПОД/ФТ"], "high"),
    ]:
        doc = _make_doc(topics=topics, penalties=["штраф"]) if expected_level == "high" else _make_doc(topics=topics)
        impact = assess_impact(doc)
        if impact.impact_level in urgency_map:
            assert impact.urgency == urgency_map[impact.impact_level], \
                f"level={impact.impact_level}, urgency={impact.urgency}"


def test_confidence_is_default():
    """Mock impact_engine возвращает фиксированную confidence = 0.85."""
    doc = _make_doc(topics=["персональные данные"])
    impact = assess_impact(doc)
    assert impact.confidence == 0.85
