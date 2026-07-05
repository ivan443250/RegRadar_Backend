"""Regression tests for securities and financial-market rule intelligence."""


SECURITIES_DECREE = """УКАЗ
ПРЕЗИДЕНТА РОССИЙСКОЙ ФЕДЕРАЦИИ

О временных мерах, связанных с публичным обращением ценных бумаг

В соответствии с Федеральным законом от 22 апреля 1996 г. № 39-ФЗ
«О рынке ценных бумаг» устанавливаются временные меры.
Положения применяются к публичному акционерному обществу и стратегическим
акционерным обществам.
Организаторы торговли учитывают требования при включении ценных бумаг
в котировальный список.
Центральному банку Российской Федерации обеспечить принятие необходимых мер.
Настоящий Указ действует до 31 июля 2028 г."""


CLIENTS = [
    {
        "client_id": "shop-1",
        "company_name": "ООО Интернет-магазин",
        "industry": "e-commerce",
        "handles_personal_data": True,
    },
    {
        "client_id": "retail-1",
        "company_name": "ООО Ритейл",
        "industry": "retail",
        "cash_operations_level": "high",
    },
    {
        "client_id": "saas-1",
        "company_name": "ООО SaaS",
        "industry": "IT/SaaS",
        "handles_personal_data": True,
    },
    {
        "client_id": "broker-plus-1",
        "company_name": "АО «Брокер Плюс»",
        "okved": "66.12",
        "industry": "securities",
        "size": "medium",
        "handles_personal_data": True,
        "cash_operations_level": "low",
        "risk_profile": "medium",
        "bank_segment": "corporate",
        "tags": ["broker", "securities_market", "exchange_trading"],
    },
]


def _analyze(client):
    response = client.post(
        "/api/ai/full-analysis",
        json={"text": SECURITIES_DECREE, "client_profiles": CLIENTS},
    )
    assert response.status_code == 200
    return response.json()


def test_securities_decree_has_financial_topic(client):
    data = _analyze(client)
    topics = " ".join(data["document_analysis"]["topics"]).lower()
    assert "ценные бумаги" in topics or "финансовый рынок" in topics
    assert "общее регулирование" not in topics


def test_securities_decree_type_and_readable_title(client):
    document = _analyze(client)["document_analysis"]
    assert document["document_type"] == "указ"
    assert document["title"] == (
        "Указ Президента РФ о временных мерах, связанных с публичным "
        "обращением ценных бумаг"
    )
    assert document["document_type"] != "Федеральный закон"


def test_securities_decree_has_medium_specialized_impact(client):
    impact = _analyze(client)["impact_assessment"]
    assert 40 <= impact["impact_score"] <= 60
    assert impact["impact_level"] == "medium"
    assert "ценных бумаг" in impact["reasoning"].lower()


def test_only_securities_client_matches(client):
    relevance = _analyze(client)["client_relevance"]
    assert [item["client_id"] for item in relevance] == ["broker-plus-1"]
    assert relevance[0]["relevance_level"] in {"medium", "high"}
    assert not any("Общая деятельность" in item for item in relevance[0]["matched_factors"])


def test_only_securities_client_receives_notification(client):
    notifications = _analyze(client)["notification_drafts"]
    assert [item["client_id"] for item in notifications] == ["broker-plus-1"]
    assert "участвует в операциях с ценными бумагами" in notifications[0]["short_message"]


def test_securities_evidence_is_verbatim_and_covers_key_triggers(client):
    fragments = _analyze(client)["document_analysis"]["source_fragments"]
    joined = " ".join(fragments).lower()

    assert fragments
    assert all(fragment in SECURITIES_DECREE for fragment in fragments)
    assert "публичным обращением ценных бумаг" in joined
    assert "о рынке ценных бумаг" in joined
    assert "организаторы торговли" in joined
    assert "котировальный список" in joined
    assert "центральному банку российской федерации" in joined
    assert "действует до 31 июля 2028" in joined


def test_industry_only_financial_profile_can_match(client):
    response = client.post(
        "/api/ai/full-analysis",
        json={
            "text": SECURITIES_DECREE,
            "client_profiles": [
                {
                    "client_id": "investment-1",
                    "company_name": "ООО Инвестиции",
                    "industry": "investment",
                }
            ],
        },
    )

    assert [
        item["client_id"] for item in response.json()["client_relevance"]
    ] == ["investment-1"]
