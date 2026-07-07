"""Personalized client matching for request profiles and seed fallback."""


PD_TEXT = (
    "Новые требования 152-ФЗ регулируют обработку персональных данных. "
    "Организации должны хранить согласия клиентов."
)

VED_TEXT = (
    "Проект устанавливает новые требования к ВЭД, импорту и экспортным "
    "операциям."
)


def test_full_analysis_without_profiles_uses_seed_fallback(client):
    response = client.post("/api/ai/full-analysis", json={"text": PD_TEXT})
    data = response.json()

    assert response.status_code == 200
    assert data["analysis_metadata"]["client_profiles_source"] == "seed_fallback"
    assert any(item["client_id"].startswith("seed-") for item in data["client_relevance"])


def test_full_analysis_with_empty_profiles_uses_seed_fallback(client):
    response = client.post(
        "/api/ai/full-analysis",
        json={"text": PD_TEXT, "client_profiles": []},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["analysis_metadata"]["client_profiles_source"] == "seed_fallback"
    assert data["client_relevance"]


def test_personal_data_profile_controls_relevance_and_notifications(client):
    response = client.post(
        "/api/ai/full-analysis",
        json={
            "text": PD_TEXT,
            "client_profiles": [
                {
                    "client_id": "custom-pd",
                    "company_name": "ООО Персональный Контур",
                    "industry": "IT",
                    "handles_personal_data": True,
                }
            ],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["analysis_metadata"]["client_profiles_source"] == "request"
    assert [item["client_id"] for item in data["client_relevance"]] == ["custom-pd"]
    assert [item["client_id"] for item in data["notification_drafts"]] == ["custom-pd"]


def test_foreign_trade_profile_matches_ved_document(client):
    response = client.post(
        "/api/ai/full-analysis",
        json={
            "text": VED_TEXT,
            "client_profiles": [
                {
                    "client_id": "custom-ved",
                    "company_name": "ООО Экспорт Плюс",
                    "has_foreign_trade": True,
                }
            ],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["analysis_metadata"]["client_profiles_source"] == "request"
    assert [item["client_id"] for item in data["client_relevance"]] == ["custom-ved"]
    assert [item["client_id"] for item in data["notification_drafts"]] == ["custom-ved"]
