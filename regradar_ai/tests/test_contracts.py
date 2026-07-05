"""Negative tests for hardened Pydantic contracts."""

import pytest
from pydantic import ValidationError

from app.ai.schemas import (
    CreateEventCardRequest,
    DocumentAnalysis,
    FullAIAnalysisRequest,
    ImpactAssessment,
)
from app.ai.gateway.base import LLMCallLogRecord
from app.models import AnalyzeRequest


def _impact(**updates) -> ImpactAssessment:
    values = {
        "impact_score": 0,
        "impact_level": "low",
        "bank_impact": "Нет влияния",
        "client_impact": "Нет влияния",
        "urgency": "low",
        "reasoning": "Нет факторов",
    }
    values.update(updates)
    return ImpactAssessment(**values)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_outside_range_is_rejected(confidence):
    with pytest.raises(ValidationError):
        DocumentAnalysis(
            title="Документ",
            short_summary="Описание",
            confidence=confidence,
        )


@pytest.mark.parametrize("impact_score", [-1, 101])
def test_impact_score_outside_range_is_rejected(impact_score):
    with pytest.raises(ValidationError):
        _impact(impact_score=impact_score)


def test_unknown_impact_level_is_rejected():
    with pytest.raises(ValidationError):
        _impact(impact_level="severe")


@pytest.mark.parametrize(
    "request_model",
    [AnalyzeRequest, FullAIAnalysisRequest, CreateEventCardRequest],
)
def test_empty_request_text_is_rejected(request_model):
    with pytest.raises(ValidationError):
        request_model(text="   ")


def test_empty_full_analysis_text_returns_422(client):
    response = client.post("/api/ai/full-analysis", json={"text": "   "})
    assert response.status_code == 422


def test_source_fragments_reject_none_items():
    with pytest.raises(ValidationError):
        DocumentAnalysis(
            title="Документ",
            short_summary="Описание",
            source_fragments=[None],
        )


def test_unknown_gateway_status_is_rejected():
    with pytest.raises(ValidationError):
        LLMCallLogRecord(
            provider="mock",
            model="mock-reg-radar-v1",
            status="pending",
            latency_ms=0,
        )
