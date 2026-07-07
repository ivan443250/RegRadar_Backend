import re

from .schemas import DocumentAnalysis, ImpactAssessment
from .financial_market_rules import is_financial_market_topic
from .fuel_excise_rules import is_fuel_excise_topic
from .domain_rules import NEUTRAL_DOMAIN, get_domain_rule


def _normalize_evidence(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().rstrip(".!?").casefold()


def _score_to_level(score: int) -> str:
    if score <= 30:
        return "low"
    elif score <= 60:
        return "medium"
    elif score <= 80:
        return "high"
    else:
        return "critical"


def assess_impact(doc: DocumentAnalysis) -> ImpactAssessment:
    """Explainable impact scoring на основе тем и триггеров документа.

    Правила:
    - персональные данные / 152-ФЗ: +30
    - 115-ФЗ / ПОД/ФТ: +35
    - ВЭД / валютный контроль: +25
    - штрафы / санкции / ответственность: +20
    - обязательства / требования / должны: +10
    - если затронуто >1 темы: +10
    - score ограничен от 0 до 100
    """
    score = 0
    reasons: list[str] = []
    evidence: list[str] = []

    topic_lower = " ".join(doc.topics).lower()
    source_text = " ".join(doc.source_fragments).lower()

    def add_matching_evidence(markers: tuple[str, ...]) -> None:
        evidence.extend(
            fragment
            for fragment in doc.source_fragments
            if any(marker in fragment.lower() for marker in markers)
        )

    financial_market = is_financial_market_topic(doc.topics)
    if financial_market:
        score += 25
        reasons.append("Документ регулирует рынок ценных бумаг (+25)")
        add_matching_evidence(("ценн", "рынке ценных бумаг"))

        if any(
            marker in source_text
            for marker in ("организатор", "котировальн")
        ):
            score += 20
            reasons.append(
                "Затронуты организаторы торговли или котировальные списки (+20)"
            )
            add_matching_evidence(("организатор", "котировальн"))

        if "публичн" in source_text and "акционерн" in source_text:
            score += 15
            reasons.append("Затронуты публичные акционерные общества (+15)")
            add_matching_evidence(("публичн",))

        if any(
            marker in source_text
            for marker in ("центральн", "банк россии")
        ):
            score += 15
            reasons.append("Документ затрагивает полномочия Банка России (+15)")
            add_matching_evidence(("центральн", "банк россии"))

        if doc.key_dates:
            score += 10
            reasons.append("Указан срок действия или значимая дата (+10)")
            add_matching_evidence(tuple(doc.key_dates))

        obligation_text = " ".join(doc.obligations).lower()
        if doc.obligations and any(
            marker in obligation_text
            for marker in ("правительств", "центральн", "банк россии")
        ):
            score += 10
            reasons.append("Установлены поручения Правительству или Банку России (+10)")

    fuel_excise = is_fuel_excise_topic(doc.topics)
    if fuel_excise:
        if any(marker in source_text for marker in ("бензин", "дизельн")):
            score += 20
            reasons.append("Затронуты бензин или дизельное топливо (+20)")
            add_matching_evidence(("бензин", "дизельн"))

        if any(
            marker in source_text
            for marker in ("нефтяного сырья", "нефтепереработ")
        ):
            score += 20
            reasons.append("Затронуты нефтяное сырьё или нефтепереработка (+20)")
            add_matching_evidence(("нефтяного сырья", "нефтепереработ"))

        if "бирж" in source_text and "торг" in source_text:
            score += 20
            reasons.append("Регулируются биржевые торги топливом (+20)")
            add_matching_evidence(("бирж",))

        if "акциз" in source_text or "налогов" in source_text:
            score += 20
            reasons.append("Затронуты акцизы или налоговый период (+20)")
            add_matching_evidence(("акциз", "налогов"))

        has_percentage_change = bool(
            re.search(r"\b\d+(?:[,.]\d+)?\s*процент", source_text)
        )
        if has_percentage_change or len(doc.key_dates) >= 2:
            score += 10
            reasons.append("Указано изменение процента или периода действия (+10)")
            add_matching_evidence(("процент", "с 1 июля", "по 30 сентября"))

        if (doc.document_type or "").casefold() == "постановление":
            score += 10
            reasons.append("Документ является постановлением Правительства (+10)")

    if "персональные данные" in topic_lower:
        score += 30
        reasons.append("Тема затрагивает обработку персональных данных (+30)")
        if doc.source_fragments:
            evidence.append(doc.source_fragments[0])

    if "115-фз" in topic_lower or "под/фт" in topic_lower:
        score += 35
        reasons.append("Тема затрагивает требования ПОД/ФТ и 115-ФЗ (+35)")
        if doc.source_fragments:
            evidence.append(doc.source_fragments[0])

    if "вэд" in topic_lower or "валютный контроль" in topic_lower:
        score += 25
        reasons.append("Тема затрагивает ВЭД и валютный контроль (+25)")
        if doc.source_fragments:
            evidence.append(doc.source_fragments[0])

    if doc.penalties_or_consequences:
        score += 20
        has_explicit_sanctions = any(
            keyword in consequence.lower()
            for consequence in doc.penalties_or_consequences
            for keyword in ("штраф", "санкц", "наказан", "приостанов")
        )
        consequence_label = (
            "санкции или штрафные меры"
            if has_explicit_sanctions
            else "ответственность или иные последствия"
        )
        reasons.append(
            f"Документ содержит {consequence_label} (+20): "
            f"{', '.join(doc.penalties_or_consequences[:2])}"
        )
        evidence.extend(doc.penalties_or_consequences[:2])

    if doc.obligations:
        score += 10
        reasons.append(f"Документ налагает обязательства (+10): {', '.join(doc.obligations[:2])}")
        evidence.extend(doc.obligations[:2])

    if doc.obligations and doc.penalties_or_consequences:
        score += 10
        reasons.append(
            "Одновременно установлены обязательства и последствия их нарушения (+10)"
        )

    if len(doc.topics) > 1:
        score += 10
        reasons.append(f"Затронуто несколько тем ({len(doc.topics)}), что увеличивает сложность (+10)")

    other_specialized_topics = any(
        marker in topic_lower
        for marker in ("персональные данные", "115-фз", "под/фт", "вэд")
    )
    if (
        financial_market
        and not other_specialized_topics
        and not doc.penalties_or_consequences
        and score > 60
    ):
        score = 60
        reasons.append(
            "Специализированное регулирование без явных санкций ограничено "
            "уровнем medium (cap 60)"
        )

    other_fuel_topics = any(
        marker in topic_lower
        for marker in (
            "персональные данные",
            "115-фз",
            "под/фт",
            "вэд",
            "ценные бумаги",
            "финансовый рынок",
        )
    )
    if (
        fuel_excise
        and not other_fuel_topics
        and not doc.penalties_or_consequences
        and score > 60
    ):
        score = 60
        reasons.append(
            "Специализированное топливное регулирование без явных санкций "
            "ограничено уровнем medium (cap 60)"
        )

    domain_rule = get_domain_rule(doc.domain)
    if domain_rule:
        if score < domain_rule.impact_floor:
            reasons.append(
                f"Базовый порог домена {domain_rule.domain} "
                f"({domain_rule.impact_floor})"
            )
        score = max(score, domain_rule.impact_floor)
        if not doc.penalties_or_consequences:
            score = min(score, domain_rule.impact_cap)
    elif doc.domain == NEUTRAL_DOMAIN:
        score = min(score, 30)

    score = max(0, min(score, 100))
    level = _score_to_level(score)

    # --- Bank / Client impact text ---
    if level == "critical":
        bank_impact = "Критическое влияние на операционные процессы банка. Требуется немедленная реакция комплаенс-подразделения."
        client_impact = "Критическое влияние на бизнес-процессы. Требуется немедленный пересмотр внутренних политик и процедур."
        urgency = "critical"
    elif level == "high":
        bank_impact = "Высокое влияние. Требуется пересмотр регламентов в кратчайшие сроки."
        client_impact = "Значительное влияние на бизнес. Рекомендуется пересмотреть процессы в течение месяца."
        urgency = "high"
    elif level == "medium":
        bank_impact = "Умеренное влияние. Требуется анализ и возможная корректировка процедур."
        client_impact = "Умеренное влияние. Рекомендуется ознакомиться и оценить необходимость изменений."
        urgency = "medium"
    else:
        bank_impact = "Низкое влияние. Мониторинг в плановом порядке."
        client_impact = "Низкое влияние. Рекомендуется принять к сведению."
        urgency = "low"

    # --- Affected processes ---
    affected_processes = list(doc.affected_processes)

    # --- Possible consequences (без выдумывания) ---
    possible_consequences: list[str] = []
    if doc.penalties_or_consequences:
        for consequence in doc.penalties_or_consequences[:2]:
            consequence_lower = consequence.lower()
            if "штраф" in consequence_lower:
                possible_consequences.append(
                    f"Возможны штрафные санкции: {consequence}"
                )
            elif "ответствен" in consequence_lower:
                possible_consequences.append(
                    "Возможны последствия, связанные с ответственностью за "
                    "нарушение требований."
                )
            elif "санкц" in consequence_lower:
                possible_consequences.append(f"Возможны санкции: {consequence}")
            else:
                possible_consequences.append(f"Возможны последствия: {consequence}")
    elif doc.obligations:
        possible_consequences = [
            "В источнике указаны обязательства, но последствия их невыполнения "
            "не уточнены."
        ]
    else:
        possible_consequences = ["Нет данных о санкциях в источнике."]

    # --- Reasoning ---
    reasoning = "; ".join(reasons) if reasons else "Нет явных триггеров для повышения скоринга."

    # --- Dedup evidence ---
    unique_evidence: list[str] = []
    seen: set[str] = set()
    for e in evidence:
        normalized = _normalize_evidence(e)
        if normalized not in seen:
            seen.add(normalized)
            unique_evidence.append(e)

    if not unique_evidence and doc.source_fragments:
        unique_evidence.append(doc.source_fragments[0])

    possible_consequences = list(dict.fromkeys(possible_consequences))

    return ImpactAssessment(
        impact_score=score,
        impact_level=level,
        bank_impact=bank_impact,
        client_impact=client_impact,
        urgency=urgency,
        affected_processes=affected_processes[:5],
        possible_consequences=possible_consequences,
        reasoning=reasoning,
        evidence_fragments=unique_evidence[:5],
        confidence=0.85,
    )
