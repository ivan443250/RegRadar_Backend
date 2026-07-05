import re

from .schemas import DocumentAnalysis
from .financial_market_rules import (
    FINANCIAL_DOCUMENT_KEYWORDS,
    FINANCIAL_MARKET_TOPIC,
)
from .fuel_excise_rules import (
    FUEL_DOCUMENT_KEYWORDS,
    FUEL_EXCISE_TOPIC,
    is_fuel_excise_topic,
)
from .domain_rules import NEUTRAL_DOMAIN, NEUTRAL_TOPICS, detect_domain


# --- Keyword rules ---

TOPIC_RULES: list[dict] = [
    {
        "topic": FUEL_EXCISE_TOPIC,
        "keywords": list(FUEL_DOCUMENT_KEYWORDS),
        "industries": [
            "топливный рынок",
            "нефтепереработка",
            "нефтепродукты",
        ],
        "processes": [
            "биржевые торги топливом",
            "реализация бензина и дизельного топлива",
            "нефтепереработка",
            "акцизы",
            "налоговый период",
            "операции с нефтяным сырьём",
        ],
    },
    {
        "topic": FINANCIAL_MARKET_TOPIC,
        "keywords": list(FINANCIAL_DOCUMENT_KEYWORDS),
        "industries": [
            "финансовый рынок",
            "рынок ценных бумаг",
            "публичное акционерное общество",
        ],
        "processes": [
            "публичное обращение ценных бумаг",
            "организация торговли",
            "листинг ценных бумаг",
            "корпоративное управление",
        ],
    },
    {
        "topic": "персональные данные",
        "keywords": [
            "персональные данные",
            "персональных данных",
            "персональными данными",
            "152-фз",
        ],
        "industries": ["IT", "ритейл", "финансы"],
        "processes": ["обработка персональных данных", "хранение данных", "уведомление Роскомнадзора"],
    },
    {
        "topic": "115-ФЗ / ПОД/ФТ",
        "keywords": ["115-фз", "под/фт", "идентификация"],
        "industries": ["финансы", "ритейл", "услуги"],
        "processes": ["идентификация клиентов", "ПОД/ФТ", "комплаенс"],
    },
    {
        "topic": "ВЭД",
        "keywords": ["вэд", "импорт", "экспорт", "валютный контроль"],
        "industries": ["логистика", "торговля", "производство"],
        "processes": ["таможенное оформление", "валютный контроль", "внешнеторговые операции"],
    },
]

OBLIGATION_KEYWORDS = [
    "обязан",
    "требуется",
    "должны",
    "необходимо",
    "надлежит",
    "обеспечить",
    "представить",
    "принять меры",
]
RESTRICTION_KEYWORDS = ["запрещается", "не допускается", "ограничивается", "не вправе"]
PENALTY_KEYWORDS = ["штраф", "санкции", "ответственность", "наказание", "приостановление"]
EFFECTIVE_DATE_KEYWORDS = ["действует до", "вступает в силу", "срок действия"]


def _normalize_fragment(text: str) -> str:
    """Нормализовать fragment для дедупликации без изменения исходного текста."""
    return re.sub(r"\s+", " ", text).strip().rstrip(".!?").casefold()


def _find_fragments(text: str, keywords: list[str]) -> list[str]:
    """Найти целые предложения с keywords, не разрезая слова."""
    fragments: list[str] = []
    seen: set[str] = set()
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    for sentence in sentences:
        fragment = sentence.strip()
        fragment_lower = fragment.lower()
        if not fragment or not any(keyword in fragment_lower for keyword in keywords):
            continue
        normalized = _normalize_fragment(fragment)
        if normalized and normalized not in seen:
            seen.add(normalized)
            fragments.append(fragment)

    return fragments[:20]


def _extract_title(text: str, lower: str) -> str:
    """Prefer a recognizable official heading over an arbitrary text prefix."""
    is_presidential_decree = (
        "указ" in lower and "президента российской федерации" in lower
    )
    securities_heading = re.search(
        r"о\s+временных\s+мерах\s*,?\s*связанных\s+с\s+публичным\s+"
        r"обращением\s+ценных\s+бумаг",
        lower,
    )
    if is_presidential_decree and securities_heading:
        return (
            "Указ Президента РФ о временных мерах, связанных с публичным "
            "обращением ценных бумаг"
        )

    is_government_resolution = (
        "правительство российской федерации" in lower
        and "постановление" in lower
    )
    if is_government_resolution and any(
        marker in lower
        for marker in ("автомобильного бензина", "дизельного топлива")
    ):
        return (
            "Постановление Правительства РФ о минимальном объёме бензина и "
            "дизельного топлива на биржевых торгах"
        )

    match = re.match(r"(.+?[.!?])\s", text.strip(), flags=re.DOTALL)
    return match.group(1).strip() if match else text.strip()[:200]


def _extract_items(text: str, keywords: list[str]) -> list[str]:
    """Извлечь предложения, содержащие ключевые слова."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    items: list[str] = []
    seen: set[str] = set()
    for s in sentences:
        s_lower = s.lower()
        if any(kw in s_lower for kw in keywords):
            clean = s.strip().rstrip(".!?")
            normalized = _normalize_fragment(clean)
            if clean and len(clean) < 200 and normalized not in seen:
                seen.add(normalized)
                items.append(clean)
    return items[:5]


def analyze_document(text: str) -> DocumentAnalysis:
    """Mock AI-анализ документа на основе rule-based правил.

    Не использует реальную LLM — только keyword matching.
    """
    lower = text.lower()

    domain_rule = detect_domain(text)

    # --- Topics ---
    topics: list[str] = []
    industries: list[str] = []
    processes: list[str] = []
    all_topic_keywords: list[str] = []

    if domain_rule:
        topics.extend(domain_rule.topics)
        all_topic_keywords.extend(domain_rule.evidence_markers)
        if domain_rule.domain == "fuel_excise":
            processes.extend(
                ["биржевые торги топливом", "нефтепереработка", "акцизы"]
            )
        else:
            processes.extend(domain_rule.topics[:3])
    else:
        topics.extend(NEUTRAL_TOPICS)
        industries.append("не определено")
        processes.append("требуется экспертная классификация")

    # --- Obligations / Restrictions / Penalties ---
    obligations = _extract_items(text, OBLIGATION_KEYWORDS)
    restrictions = _extract_items(text, RESTRICTION_KEYWORDS)
    penalties = _extract_items(text, PENALTY_KEYWORDS)

    # --- Source fragments ---
    evidence_keywords = list(
        dict.fromkeys(
            (all_topic_keywords or ["утверждены правила", "срок", "регулирование", "закон", "требование"])
            + OBLIGATION_KEYWORDS
            + RESTRICTION_KEYWORDS
            + PENALTY_KEYWORDS
            + EFFECTIVE_DATE_KEYWORDS
            + ["утверждены правила", "срок", "внесены изменения", "вступает в силу"]
        )
    )
    if is_fuel_excise_topic(topics):
        evidence_keywords.extend(
            ["процент", "с 1 июля", "по 30 сентября", "налогового периода"]
        )
    source_fragments = _find_fragments(text, evidence_keywords)
    if not source_fragments:
        fallback = next(
            (part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()),
            text.strip()[:500],
        )
        if fallback:
            source_fragments = [fallback]

    # --- Title / Summary ---
    title = _extract_title(text, lower)
    short_summary = text[:300] + ("..." if len(text) > 300 else "")
    long_summary = text[:800] + ("..." if len(text) > 800 else "")

    # --- Regulator / Document type / Status ---
    regulator = None
    if "роскомнадзор" in lower:
        regulator = "Роскомнадзор"
    elif any(
        marker in lower
        for marker in (
            "цб",
            "центральный банк",
            "центральному банку",
            "банк россии",
        )
    ):
        regulator = "Центральный банк РФ"
    elif "фнс" in lower or "налоговая" in lower:
        regulator = "ФНС России"
    elif "минфин" in lower:
        regulator = "Минфин России"
    elif "правительство" in lower:
        regulator = "Правительство РФ"

    document_type = None
    heading = lower[:600]
    if re.match(r"\s*проект(?:\s|$)", heading):
        document_type = "Проект"
    elif "распоряжение президента российской федерации" in heading:
        document_type = "распоряжение президента"
    elif "распоряжение" in heading:
        document_type = "распоряжение"
    elif "постановление" in heading:
        document_type = "постановление"
    elif "указ" in heading and "президента российской федерации" in heading:
        document_type = "указ"
    elif "федеральный закон" in heading:
        document_type = "федеральный закон"
    elif "приказ" in heading:
        document_type = "приказ"
    elif "указ" in heading:
        document_type = "указ"
    elif "письмо" in heading:
        document_type = "письмо"

    status = None
    if "проект" in lower:
        status = "проект"
    elif "вступил" in lower or "вступает" in lower:
        status = "вступает в силу"
    elif "действует" in lower:
        status = "действующий"

    # --- Key dates ---
    key_dates = re.findall(
        r"\b\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\b",
        lower,
    )
    key_dates = key_dates[:3]

    return DocumentAnalysis(
        title=title,
        short_summary=short_summary,
        long_summary=long_summary,
        domain=domain_rule.domain if domain_rule else NEUTRAL_DOMAIN,
        regulator=regulator,
        document_type=document_type,
        status=status,
        topics=topics,
        affected_industries=industries,
        affected_processes=processes,
        key_dates=key_dates,
        obligations=obligations,
        restrictions=restrictions,
        penalties_or_consequences=penalties,
        source_fragments=source_fragments,
        confidence=0.85,
    )
