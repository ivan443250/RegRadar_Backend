"""Shared rule markers for fuel, oil-processing and excise documents."""


FUEL_EXCISE_TOPIC = "топливный рынок / акцизы"

FUEL_DOCUMENT_KEYWORDS = (
    "автомобильного бензина",
    "автомобильный бензин",
    "бензина класса 5",
    "дизельного топлива",
    "дизельное топливо",
    "дизельного топлива класса 5",
    "нефтяного сырья",
    "переработке нефтяного сырья",
    "нефтепереработ",
    "акциз",
    "акцизы",
    "налоговый период по акцизам",
    "биржевые торги",
    "биржевых торгах",
    "биржей",
    "минимальной величины объема",
    "минимального объёма",
    "реализованных налогоплательщиком",
    "свидетельство о регистрации лица, совершающего операции по переработке нефтяного сырья",
)

FUEL_CLIENT_MARKERS = (
    "fuel_trade",
    "oil_processing",
    "petroleum",
    "gas_station",
    "energy",
    "fuel",
    "oil_products",
    "excise",
    "exchange_trading",
)


def is_fuel_excise_topic(topics: list[str]) -> bool:
    joined = " ".join(topics).casefold()
    return any(
        marker in joined
        for marker in ("топливный рынок", "нефтепереработка", "акцизы")
    )


def has_fuel_client_marker(keywords: list[str]) -> bool:
    joined = " ".join(keywords).casefold()
    return any(marker in joined for marker in FUEL_CLIENT_MARKERS)
