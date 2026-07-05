"""Notification disclaimer and pre-delivery safety gate tests."""

import pytest

from app.ai.notification_safety import (
    STANDARD_NOTIFICATION_DISCLAIMER,
    ensure_notification_disclaimer,
    validate_notification_can_be_sent,
)
from app.ai.schemas import NotificationDraft


def _draft(**updates):
    values = {
        "client_id": "client-1",
        "client_name": "ООО Клиент",
        "title": "Изменение регулирования",
        "short_message": "Изменение может быть релевантно для вашей организации.",
        "full_message": "Рекомендуется проверить применимость новых требований.",
        "client_friendly_explanation": "Проверьте внутренние процессы.",
        "disclaimer": "Информационное уведомление.",
        "priority": "medium",
    }
    values.update(updates)
    return NotificationDraft(**values)


def test_empty_disclaimer_is_replaced():
    result = ensure_notification_disclaimer(_draft(disclaimer=""))
    assert result.disclaimer == STANDARD_NOTIFICATION_DISCLAIMER


@pytest.mark.parametrize(
    "phrase",
    ["Вы обязаны выполнить требования", "Гарантируем результат", "Это точно применимо", "Это официальный документ"],
)
def test_categorical_phrases_are_blocked(phrase):
    errors = validate_notification_can_be_sent(
        _draft(full_message=phrase),
        [{"client_id": "client-1"}],
        {"domain": "personal_data"},
    )
    assert any("prohibited" in error for error in errors)


def test_standard_legal_disclaimer_is_not_treated_as_legal_advice():
    draft = _draft(disclaimer=STANDARD_NOTIFICATION_DISCLAIMER)
    assert validate_notification_can_be_sent(
        draft,
        [{"client_id": "client-1"}],
        {"domain": "personal_data"},
    ) == []


def test_neutral_and_irrelevant_client_are_blocked():
    neutral_errors = validate_notification_can_be_sent(
        _draft(),
        [{"client_id": "client-1"}],
        {"domain": "neutral_no_match"},
    )
    relevance_errors = validate_notification_can_be_sent(
        _draft(),
        [{"client_id": "another-client"}],
        {"domain": "personal_data"},
    )
    assert any("neutral_no_match" in error for error in neutral_errors)
    assert any("not relevant" in error for error in relevance_errors)

