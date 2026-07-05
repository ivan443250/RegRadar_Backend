"""Manifest-driven evaluation of the baseline on real legal documents."""

import re

import pytest

from app.evaluation import (
    RealSampleManifestItem,
    build_eval_client_profiles,
    load_real_sample_text,
    load_real_samples_manifest,
    run_full_analysis_for_sample,
    run_upload_card_like_flow_for_sample,
)


REAL_SAMPLES = load_real_samples_manifest(enabled_only=True)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _profile_ids_with_tags(tags: list[str]) -> set[str]:
    expected_tags = {tag.casefold() for tag in tags}
    return {
        profile.client_id
        for profile in build_eval_client_profiles()
        if expected_tags.intersection(tag.casefold() for tag in profile.tags)
    }


def test_real_samples_manifest_loads():
    assert isinstance(REAL_SAMPLES, list)
    assert len({sample.id for sample in REAL_SAMPLES}) == len(REAL_SAMPLES)
    assert len({sample.filename for sample in REAL_SAMPLES}) == len(REAL_SAMPLES)


def test_eval_client_portfolio_has_required_segments():
    profiles = build_eval_client_profiles()
    all_tags = {tag for profile in profiles for tag in profile.tags}

    assert len(profiles) == 14
    assert {
        "ecommerce",
        "foreign_trade",
        "cash_heavy",
        "saas",
        "broker",
        "fuel",
        "tax_reporting",
        "payment_service",
        "neutral",
    } <= all_tags


@pytest.mark.parametrize(
    "sample",
    REAL_SAMPLES or [None],
    ids=[sample.id for sample in REAL_SAMPLES] or ["manifest-empty"],
)
def test_real_sample_expected_outcome(
    sample: RealSampleManifestItem | None,
):
    if sample is None:
        pytest.skip(
            "Real samples manifest is empty; add TXT files and manifest entries."
        )

    analysis = run_full_analysis_for_sample(sample)
    card = run_upload_card_like_flow_for_sample(sample).event_card

    if sample.document_type_expected:
        assert _normalize(analysis.document_analysis.document_type or "") == _normalize(
            sample.document_type_expected
        )

    if sample.topics_expected:
        actual_topics = [_normalize(topic) for topic in analysis.document_analysis.topics]
        assert any(
            _normalize(expected) in actual
            for expected in sample.topics_expected
            for actual in actual_topics
        )

    if sample.domain_expected:
        assert analysis.document_analysis.domain == sample.domain_expected

    allowed_impact_levels = set(sample.impact_levels_allowed)
    if sample.impact_level_expected:
        allowed_impact_levels.add(sample.impact_level_expected)
    if allowed_impact_levels:
        assert analysis.impact_assessment.impact_level in allowed_impact_levels

    assert analysis.document_analysis.source_fragments
    assert analysis.impact_assessment.evidence_fragments
    evidence_text = _normalize(" ".join(
        analysis.document_analysis.source_fragments
        + analysis.impact_assessment.evidence_fragments
    ))
    for required_fragment in sample.evidence_must_include:
        assert _normalize(required_fragment) in evidence_text

    if sample.review_state_expected:
        assert card.review_state == sample.review_state_expected
    assert card.evidence_fragments
    source_text = load_real_sample_text(sample.filename)
    for evidence in card.evidence_fragments:
        assert evidence.document_id == sample.id
        assert evidence.version_id == "eval-v1"
        assert evidence.text in source_text
    assert any(evidence.chunk_id for evidence in card.evidence_fragments)

    notification_client_ids = {
        notification.client_id for notification in analysis.notification_drafts
    }
    relevance_client_ids = {
        relevance.client_id for relevance in analysis.client_relevance
    }
    if sample.notification_expected == "none":
        assert not notification_client_ids
        assert not relevance_client_ids
    elif sample.notification_expected == "only_relevant_clients":
        relevant_ids = _profile_ids_with_tags(sample.relevant_client_tags)
        assert notification_client_ids <= relevant_ids
        assert relevance_client_ids <= relevant_ids
        if relevant_ids:
            assert notification_client_ids

    non_relevant_ids = _profile_ids_with_tags(sample.non_relevant_client_tags)
    assert notification_client_ids.isdisjoint(non_relevant_ids)
    assert relevance_client_ids.isdisjoint(non_relevant_ids)
