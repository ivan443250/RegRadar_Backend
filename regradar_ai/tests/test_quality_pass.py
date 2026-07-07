"""Regression tests for rule-based quality issues found by manual API checks."""

import re

import pytest

from app.ai.event_card_service import create_event_card
from app.ai.impact_engine import assess_impact
from app.ai.mock_provider import analyze_document
from app.ai.schemas import ClientProfileForAI
from app.ai.service import full_ai_analysis


PD_TEXT = (
    "Проект предусматривает обработку персональных данных клиентов. "
    "Организации должны хранить согласия и соблюдать 152-ФЗ. "
    "За нарушение требований может наступать ответственность."
)

AML_TEXT = (
    "Документ уточняет требования 115-ФЗ по идентификации клиентов. "
    "Особое внимание уделяется наличным расчетам и ПОД/ФТ."
)

VED_TEXT = (
    "Проект вводит требования для участников ВЭД. Компании, осуществляющие "
    "импорт и экспорт, должны соблюдать правила валютного контроля."
)


def _profile(**updates) -> ClientProfileForAI:
    values = {
        "client_id": "client-1",
        "company_name": "ООО Тест",
        "cash_operations_level": "low",
        "risk_profile": "low",
    }
    values.update(updates)
    return ClientProfileForAI(**values)


def test_low_cash_and_low_risk_do_not_match_aml():
    result = full_ai_analysis(AML_TEXT, [_profile()])
    assert result.client_relevance == []
    assert result.notification_drafts == []


@pytest.mark.parametrize("cash_level", ["medium", "high"])
def test_medium_or_high_cash_can_match_aml(cash_level):
    result = full_ai_analysis(
        AML_TEXT,
        [_profile(cash_operations_level=cash_level)],
    )
    assert [item.client_id for item in result.client_relevance] == ["client-1"]
    assert result.client_relevance[0].matched_factors == [
        f"Наличные операции: {cash_level}"
    ]


def test_high_risk_can_match_aml_without_high_cash():
    result = full_ai_analysis(
        AML_TEXT,
        [_profile(cash_operations_level="low", risk_profile="high")],
    )
    assert result.client_relevance[0].matched_factors == ["Повышенный risk_profile"]


def test_152fz_factors_do_not_include_aml():
    profile = _profile(
        handles_personal_data=True,
        uses_online_payments=True,
    )
    factors = full_ai_analysis(PD_TEXT, [profile]).client_relevance[0].matched_factors
    assert "Обработка персональных данных" in factors
    assert "Онлайн-платежи с использованием клиентских данных" in factors
    assert not any("ПОД/ФТ" in factor for factor in factors)


def test_ved_factors_do_not_include_aml_for_low_cash():
    profile = _profile(has_foreign_trade=True)
    factors = full_ai_analysis(VED_TEXT, [profile]).client_relevance[0].matched_factors
    assert "ВЭД" in factors
    assert "Импорт/экспорт" in factors
    assert "Валютный контроль" in factors
    assert not any("ПОД/ФТ" in factor for factor in factors)


def test_obligations_and_responsibility_raise_152fz_impact_to_high():
    result = full_ai_analysis(PD_TEXT)
    assert result.impact_assessment.impact_score > 60
    assert result.impact_assessment.impact_level == "high"


@pytest.mark.parametrize("law_reference", ["152-ФЗ", "115-ФЗ"])
def test_law_reference_alone_does_not_set_federal_law_type(law_reference):
    document = analyze_document(f"Документ уточняет требования {law_reference}.")
    assert document.document_type is None


def test_project_is_classified_as_project_not_federal_law():
    document = analyze_document("Проект изменяет требования 152-ФЗ.")
    assert document.document_type == "Проект"


def test_responsibility_without_fine_does_not_invent_fine():
    impact = assess_impact(analyze_document(PD_TEXT))
    assert impact.possible_consequences
    assert all("штраф" not in item.lower() for item in impact.possible_consequences)
    assert any("ответственност" in item.lower() for item in impact.possible_consequences)


def test_evidence_is_verbatim_sentence_based_and_deduplicated():
    document = analyze_document(PD_TEXT)
    normalized = [
        re.sub(r"\s+", " ", item).strip().rstrip(".!?").casefold()
        for item in document.source_fragments
    ]

    assert len(normalized) == len(set(normalized))
    assert all(fragment in PD_TEXT for fragment in document.source_fragments)
    assert any("персональных данных" in item for item in document.source_fragments)
    assert any("152-ФЗ" in item and "должны" in item for item in document.source_fragments)
    assert any("ответственность" in item for item in document.source_fragments)


def test_event_card_deduplicates_evidence_and_requires_review():
    card = create_event_card(PD_TEXT)
    normalized = [
        re.sub(r"\s+", " ", item.text).strip().rstrip(".!?").casefold()
        for item in card.evidence_fragments
    ]

    assert len(normalized) == len(set(normalized))
    assert card.review_state == "needs_review"
    assert card.review_required is True
    assert card.analysis_metadata.fallback_used is False
