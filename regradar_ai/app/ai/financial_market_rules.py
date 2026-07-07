"""Shared rule markers for securities and financial-market documents."""


FINANCIAL_MARKET_TOPIC = "ценные бумаги"

FINANCIAL_DOCUMENT_KEYWORDS = (
    "ценных бумаг",
    "рынке ценных бумаг",
    "публичное обращение ценных бумаг",
    "публичного акционерного общества",
    "публичному акционерному обществу",
    "публичные акционерные общества",
    "организаторы торговли",
    "организаторов торговли",
    "котировальный список",
    "котировального списка",
    "корпоративное управление",
    "совет директоров",
    "независимые директора",
    "независимых директоров",
    "независимым директорам",
    "стратегические предприятия",
    "стратегических предприятий",
    "стратегических акционерных обществ",
    "центральному банку российской федерации",
    "центральный банк российской федерации",
    "банк россии",
)

FINANCIAL_CLIENT_MARKERS = (
    "securities",
    "brokerage",
    "broker",
    "investment",
    "investment_company",
    "issuer",
    "public_company",
    "securities_market",
    "exchange_trading",
    "financial_market",
    "strategic_enterprise",
)


def is_financial_market_topic(topics: list[str]) -> bool:
    joined = " ".join(topics).casefold()
    return "ценные бумаги" in joined or "финансовый рынок" in joined


def has_financial_client_marker(keywords: list[str]) -> bool:
    joined = " ".join(keywords).casefold()
    return any(marker in joined for marker in FINANCIAL_CLIENT_MARKERS)
