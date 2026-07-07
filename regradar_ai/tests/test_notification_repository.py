"""JSONL repository tests for mock notification deliveries."""

import pytest

from app.storage import notification_repository


@pytest.fixture(autouse=True)
def isolated_notifications(tmp_path, monkeypatch):
    path = tmp_path / "notifications.jsonl"
    monkeypatch.setattr(notification_repository, "NOTIFICATIONS_PATH", path)
    return path


def _record(delivery_id="delivery-1", client_id="client-1", document_id="doc-1"):
    return notification_repository.NotificationDeliveryRecord(
        notification_id="notification-1",
        delivery_id=delivery_id,
        document_id=document_id,
        client_id=client_id,
        client_name="ООО Клиент",
        notification_title="Изменение регулирования",
        channel="mock",
        status="sent_mock",
        priority="medium",
        disclaimer="Информационное уведомление.",
        source_chunk_ids=["chunk_1"],
        payload_preview={"full_message": "x" * 2500, "api_key": "secret"},
    )


def test_save_delivery_creates_jsonl(isolated_notifications):
    assert notification_repository.save_delivery(_record()) is True
    assert isolated_notifications.exists()
    assert len(isolated_notifications.read_text(encoding="utf-8").splitlines()) == 1


def test_delivery_queries():
    notification_repository.save_delivery(_record())
    notification_repository.save_delivery(
        _record("delivery-2", "client-2", "doc-2")
    )
    assert notification_repository.list_deliveries()[0]["delivery_id"] == "delivery-2"
    assert notification_repository.list_deliveries_by_document("doc-1")[0]["delivery_id"] == "delivery-1"
    assert notification_repository.list_deliveries_by_client("client-2")[0]["delivery_id"] == "delivery-2"
    assert notification_repository.get_delivery("delivery-1")["client_id"] == "client-1"


def test_payload_preview_is_bounded_and_secret_free(isolated_notifications):
    notification_repository.save_delivery(_record())
    raw = isolated_notifications.read_text(encoding="utf-8")
    record = notification_repository.get_delivery("delivery-1")
    assert "secret" not in raw
    assert "api_key" not in raw
    assert len(record["payload_preview"]["full_message"]) == 2000

