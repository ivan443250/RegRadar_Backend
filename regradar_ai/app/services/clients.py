from dataclasses import dataclass


@dataclass
class SeedClient:
    name: str
    segment: str
    keywords: list[str]


SEED_CLIENTS: list[SeedClient] = [
    SeedClient(
        name="ООО «Онлайн-Шоп»",
        segment="интернет-магазин",
        keywords=["персональные данные", "152-фз", "онлайн", "клиент"],
    ),
    SeedClient(
        name="ООО «ТрансГлобалИмпорт»",
        segment="импортер",
        keywords=["вэд", "импорт", "таможня", "экспорт"],
    ),
    SeedClient(
        name="ООО «ВкусСеть»",
        segment="ресторанная сеть",
        keywords=["наличные", "эквайринг", "санитарные", "115-фз"],
    ),
    SeedClient(
        name="ООО «Облачные Технологии»",
        segment="IT/SaaS-компания",
        keywords=["152-фз", "персональные данные", "экспорт", "импорт"],
    ),
    SeedClient(
        name="ООО «Наличные Активы»",
        segment="компания с большим объемом наличных операций",
        keywords=["115-фз", "под/фт", "идентификация", "наличные"],
    ),
    SeedClient(
        name="ООО «Топливный Трейдер»",
        segment="торговля нефтепродуктами",
        keywords=[
            "fuel_trade",
            "fuel",
            "oil_products",
            "excise",
            "exchange_trading",
        ],
    ),
]
