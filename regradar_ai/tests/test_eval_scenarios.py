"""Eval-тесты для основных сценариев регуляторных документов.

Проверяют качество rule-based анализа на типичных входных данных.
"""


import pytest


DISCLAIMER_FRAGMENT = "не является юридической рекомендацией"


# --- Сценарий 1: 152-ФЗ / персональные данные ---


TEXT_152FZ = (
    "Проект предусматривает новые требования к обработке персональных данных "
    "клиентов. Организации должны обеспечить хранение согласий пользователей "
    "и соблюдать положения 152-ФЗ. За нарушение требований может наступать "
    "ответственность."
)


def test_152fz_topics(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_152FZ}).json()
    topics = data["document_analysis"]["topics"]
    topics_lower = " ".join(topics).lower()
    assert "персональные данные" in topics_lower or "152-фз" in topics_lower


def test_152fz_impact_level(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_152FZ}).json()
    impact = data["impact_assessment"]
    # 152-ФЗ (+30) + obligations (+10) + penalties (+20) = 60 = medium
    assert impact["impact_level"] in {"medium", "high", "critical"}
    assert impact["impact_score"] >= 50


def test_152fz_evidence(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_152FZ}).json()
    doc = data["document_analysis"]
    assert doc["source_fragments"], "Должны быть source_fragments для 152-ФЗ"


def test_152fz_notifications_disclaimer(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_152FZ}).json()
    notifications = data["notification_drafts"]
    assert len(notifications) > 0
    for n in notifications:
        assert DISCLAIMER_FRAGMENT in n["disclaimer"]


def test_152fz_relevant_clients(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_152FZ}).json()
    client_names = [c["client_name"].lower() for c in data["client_relevance"]]
    assert any("онлайн" in name or "облачн" in name for name in client_names), \
        f"Ожидались клиенты типа интернет-магазин/IT/SaaS, получили: {client_names}"


# --- Сценарий 2: 115-ФЗ / ПОД/ФТ ---


TEXT_115FZ = (
    "Документ уточняет требования 115-ФЗ по идентификации клиентов и контролю "
    "подозрительных операций. Особое внимание уделяется наличным расчетам и "
    "операциям с повышенным риском."
)


def test_115fz_topics(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_115FZ}).json()
    topics = " ".join(data["document_analysis"]["topics"]).lower()
    assert "115-фз" in topics or "под/фт" in topics


def test_115fz_impact_level(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_115FZ}).json()
    impact = data["impact_assessment"]
    # 115-ФЗ (+35) → score 35 = medium; с наличными/идентификацией может быть +10
    assert impact["impact_level"] in {"medium", "high", "critical"}
    assert impact["impact_score"] >= 30


def test_115fz_reasoning(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_115FZ}).json()
    assert data["impact_assessment"]["reasoning"], "Reasoning не должен быть пустым"


def test_115fz_evidence(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_115FZ}).json()
    doc = data["document_analysis"]
    assert doc["source_fragments"], "Должны быть source_fragments для 115-ФЗ"


def test_115fz_relevant_clients(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_115FZ}).json()
    client_names = [c["client_name"].lower() for c in data["client_relevance"]]
    # Наличные операции: Наличные Активы или ВкусСеть
    assert any("наличн" in name or "вкус" in name for name in client_names), \
        f"Ожидались клиенты с наличными операциями, получили: {client_names}"


# --- Сценарий 3: ВЭД ---


TEXT_VED = (
    "Проект вводит новые требования для участников внешнеэкономической деятельности. "
    "Компании, осуществляющие импорт и экспорт товаров, должны предоставлять "
    "дополнительные документы по операциям ВЭД и валютному контролю."
)


def test_ved_topics(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_VED}).json()
    topics = " ".join(data["document_analysis"]["topics"]).lower()
    assert "вэд" in topics or "валютный контроль" in topics


def test_ved_impact_level(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_VED}).json()
    impact_level = data["impact_assessment"]["impact_level"]
    assert impact_level in {"medium", "high"}, f"impact_level={impact_level}"


def test_ved_affected_processes_or_reasoning(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_VED}).json()
    impact = data["impact_assessment"]
    assert impact["affected_processes"] or impact["reasoning"]


def test_ved_relevant_client_importer(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_VED}).json()
    client_names = [c["client_name"].lower() for c in data["client_relevance"]]
    assert any("трансглобал" in name for name in client_names), \
        f"Ожидался клиент-импортер, получили: {client_names}"


# --- Сценарий 4: общий нейтральный текст ---


TEXT_NEUTRAL = (
    "Документ содержит общие положения о развитии цифровых сервисов и "
    "повышении качества электронного взаимодействия организаций."
)


def test_neutral_impact_low_or_medium(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_NEUTRAL}).json()
    impact_level = data["impact_assessment"]["impact_level"]
    assert impact_level in {"low", "medium"}, f"impact_level={impact_level}"


def test_neutral_no_invented_penalties(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_NEUTRAL}).json()
    doc = data["document_analysis"]
    assert doc["penalties_or_consequences"] == [], \
        f"Не должно быть выдуманных штрафов: {doc['penalties_or_consequences']}"


def test_neutral_no_invented_dates(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_NEUTRAL}).json()
    doc = data["document_analysis"]
    assert doc["key_dates"] == [], \
        f"Не должно быть выдуманных дат: {doc['key_dates']}"


def test_neutral_no_invented_regulator(client):
    data = client.post("/api/ai/full-analysis", json={"text": TEXT_NEUTRAL}).json()
    doc = data["document_analysis"]
    assert doc["regulator"] is None, \
        f"Не должно быть выдуманного регулятора: {doc['regulator']}"
