"""Regression tests for fuel-market, oil-processing and excise rules."""

import json


FUEL_RESOLUTION = """ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ
ПОСТАНОВЛЕНИЕ
№ 825

О внесении изменений в требования к биржевым торгам нефтепродуктами

Установить минимальную величину объема автомобильного бензина класса 5,
реализованного налогоплательщиком на биржевых торгах, в размере 15 процентов.
Минимальная величина объема дизельного топлива класса 5, реализованного через
биржу, устанавливается в размере 10 процентов.
Требования применяются к лицам, имеющим свидетельство о регистрации лица,
совершающего операции по переработке нефтяного сырья.
Показатели определяются по итогам налогового периода по акцизам.
Изменения действуют с 1 июля 2026 г. по 30 сентября 2026 г."""


CLIENTS = [
    {
        "client_id": "shop-1",
        "company_name": "ООО Интернет-магазин",
        "industry": "e-commerce",
    },
    {
        "client_id": "saas-1",
        "company_name": "ООО SaaS",
        "industry": "IT/SaaS",
    },
    {
        "client_id": "restaurant-1",
        "company_name": "ООО Ресторан",
        "industry": "restaurant",
        "cash_operations_level": "high",
    },
    {
        "client_id": "importer-1",
        "company_name": "ООО Импортёр",
        "industry": "wholesale_trade",
        "has_foreign_trade": True,
    },
    {
        "client_id": "fuel-trade-1",
        "company_name": "ООО «Топливный Трейдер»",
        "okved": "46.71",
        "industry": "fuel_trade",
        "size": "medium",
        "cash_operations_level": "medium",
        "risk_profile": "medium",
        "bank_segment": "corporate",
        "tags": ["fuel", "oil_products", "excise", "exchange_trading"],
    },
]


def _analyze(client):
    response = client.post(
        "/api/ai/full-analysis",
        json={"text": FUEL_RESOLUTION, "client_profiles": CLIENTS},
    )
    assert response.status_code == 200
    return response.json()


def test_fuel_resolution_topic_type_and_title(client):
    document = _analyze(client)["document_analysis"]
    topics = " ".join(document["topics"]).lower()
    assert "топливный рынок" in topics or "акцизы" in topics
    assert document["document_type"] == "постановление"
    assert document["title"] == (
        "Постановление Правительства РФ о минимальном объёме бензина и "
        "дизельного топлива на биржевых торгах"
    )


def test_fuel_resolution_processes_and_medium_impact(client):
    data = _analyze(client)
    processes = data["document_analysis"]["affected_processes"]
    impact = data["impact_assessment"]

    assert "биржевые торги топливом" in processes
    assert "нефтепереработка" in processes
    assert "акцизы" in processes
    assert 40 <= impact["impact_score"] <= 60
    assert impact["impact_level"] == "medium"
    assert impact["urgency"] in {"low", "medium"}


def test_only_fuel_client_matches_and_receives_notification(client):
    data = _analyze(client)
    assert [item["client_id"] for item in data["client_relevance"]] == [
        "fuel-trade-1"
    ]
    assert [item["client_id"] for item in data["notification_drafts"]] == [
        "fuel-trade-1"
    ]
    assert "биржевыми торгами нефтепродуктами" in data["notification_drafts"][0][
        "short_message"
    ]


def test_fuel_evidence_is_verbatim_and_covers_triggers(client):
    fragments = _analyze(client)["document_analysis"]["source_fragments"]
    joined = " ".join(fragments).lower()

    assert fragments
    assert all(fragment in FUEL_RESOLUTION for fragment in fragments)
    assert "автомобильного бензина класса 5" in joined
    assert "дизельного топлива класса 5" in joined
    assert "переработке нефтяного сырья" in joined
    assert "биржевых торгах" in joined
    assert "15 процентов" in joined
    assert "10 процентов" in joined
    assert "налогового периода по акцизам" in joined
    assert "с 1 июля 2026 г. по 30 сентября 2026 г." in joined


def test_fuel_upload_card_links_evidence_to_source_chunk(client):
    response = client.post(
        "/api/documents/upload-create-card",
        files={
            "file": (
                "resolution-825.txt",
                FUEL_RESOLUTION.encode("utf-8"),
                "text/plain",
            )
        },
        data={
            "document_id": "fuel-doc-825",
            "version_id": "v1",
            "client_profiles_json": json.dumps(CLIENTS, ensure_ascii=False),
        },
    )

    assert response.status_code == 200
    card = response.json()["card"]["event_card"]
    assert card["evidence_fragments"]
    for evidence in card["evidence_fragments"]:
        assert evidence["text"] in FUEL_RESOLUTION
        assert evidence["document_id"] == "fuel-doc-825"
        assert evidence["version_id"] == "v1"
        assert evidence["chunk_id"].startswith("chunk_")


def test_unknown_document_has_no_mass_client_matching(client):
    response = client.post(
        "/api/ai/full-analysis",
        json={
            "text": "Информационный материал содержит общие сведения о мероприятии.",
            "client_profiles": CLIENTS,
        },
    )
    data = response.json()

    assert data["document_analysis"]["domain"] == "neutral_no_match"
    assert "нейтральное регулирование" in data["document_analysis"]["topics"]
    assert data["client_relevance"] == []
    assert data["notification_drafts"] == []


def test_unknown_document_event_card_stays_in_review_without_clients(client):
    response = client.post(
        "/api/events/create-card",
        json={"text": "Информационный материал о проведённом мероприятии."},
    )
    card = response.json()["event_card"]

    assert card["review_state"] == "needs_review"
    assert card["review_required"] is True
    assert card["client_relevance"] == []
    assert card["notification_drafts"] == []
