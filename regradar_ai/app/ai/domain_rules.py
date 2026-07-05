"""Generalized domain rules shared by the deterministic baseline pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainRule:
    domain: str
    topics: tuple[str, ...]
    document_markers: tuple[str, ...]
    client_markers: tuple[str, ...]
    evidence_markers: tuple[str, ...]
    impact_floor: int
    impact_cap: int


DOMAIN_RULES: tuple[DomainRule, ...] = (
    DomainRule(
        "personal_data",
        ("персональные данные", "биометрия", "идентификация"),
        (
            "персональн данн", "персональных данных", "персональными данными",
            "биометрических персональных", "идентификации пользователей",
            "сервиса обмена мгновенными сообщениями",
        ),
        ("personal_data", "biometrics", "ecommerce", "saas", "online_service", "152-фз", "персональные данные"),
        ("персональн", "биометр", "идентификац", "обработк"),
        50,
        60,
    ),
    DomainRule(
        "aml",
        ("ПОД/ФТ", "идентификация клиентов", "подозрительные операции"),
        (
            "противодействии легализации", "финансированию терроризма",
            "подозрительных операций", "бенефициарного владельца",
            "идентификации клиента", "115-фз",
        ),
        ("aml_risk", "cash_heavy", "bank", "payment_service", "foreign_financial_org", "115-фз", "под/фт", "идентификация"),
        ("легализац", "финансирован", "подозрительн", "идентификац", "бенефициар"),
        61,
        80,
    ),
    DomainRule(
        "product_marking_trade",
        ("маркировка товаров", "товарный оборот", "импорт", "медицинские изделия"),
        (
            "маркировка отдельных видов", "маркировки товаров",
            "маркировке товаров", "эксперимента по маркировке",
        ),
        ("product_marking", "import", "medical_devices", "wholesale", "retail"),
        ("маркиров", "средств идентификац", "медицинских изделий", "производител", "импортер"),
        40,
        60,
    ),
    DomainRule(
        "lending_consumer_credit",
        ("кредитование", "потребительский кредит", "банковская деятельность"),
        ("потребительского кредита", "договор потребительского кредита", "кредитная организация обязана"),
        ("bank", "lending", "consumer_credit", "financial_service"),
        ("потребительск", "кредитная организация", "договора потребительского кредита", "заемщик"),
        40,
        60,
    ),
    DomainRule(
        "fuel_excise",
        ("топливный рынок", "нефтепереработка", "акцизы", "биржевые торги"),
        (
            "акциз", "нефтяного сырья", "нефтепереработ", "сжиженные углеводородные газы",
            "минимальной величины объема автомобильного бензина", "биржевых торгах",
            "автомобильного бензина", "дизельного топлива",
        ),
        ("fuel", "oil_products", "oil_processing", "excise", "exchange_trading", "petroleum"),
        ("акциз", "бензин", "дизель", "нефтян", "биржев", "налогового периода", "срок"),
        40,
        60,
    ),
    DomainRule(
        "financial_market_securities",
        ("финансовый рынок", "ценные бумаги", "инвестиционные инструменты"),
        ("ценных бумаг", "рынке ценных бумаг", "публичным обращением ценных бумаг", "котировального списка"),
        ("broker", "securities_market", "issuer", "investment", "investment_platform", "cfa", "financial_market"),
        ("ценн", "финансов", "публичн", "котировальн", "вступает в силу"),
        40,
        60,
    ),
    DomainRule(
        "payments_digital_ruble",
        ("платежи", "переводы денежных средств", "цифровой рубль", "банковские карты"),
        (
            "операторов по переводу денежных средств", "перевода денежных средств",
            "переводу денежных средств", "электронных денежных средств",
            "платежной системы банка россии", "национального платежного инструмента",
            "электронное средство платежа",
        ),
        ("payment_service", "acquiring", "sbp", "digital_ruble", "bank_card", "operator_transfer", "online_payments", "платежи"),
        ("перевод", "платеж", "банковск", "электронных денежных", "национального платежного инструмента", "срок", "утверждены правила"),
        40,
        60,
    ),
    DomainRule(
        "tax_reporting",
        ("налоги", "налоговый контроль", "отчетность", "ФНС"),
        (
            "налогового кодекса", "налоговый орган", "налоговых органах",
            "налогоплательщик", "налоговой проверки", "декларации",
        ),
        ("tax_reporting", "accounting", "corporate_tax", "investment_project", "cash_declaration"),
        ("налог", "декларац", "отчетн", "ответствен", "вступает в силу", "срок"),
        40,
        60,
    ),
    DomainRule(
        "foreign_trade_currency_control",
        ("ВЭД", "валютное регулирование", "валютный контроль", "экспорт", "импорт"),
        (
            "валютного контроля", "валютного регулирования", "внешнеторгов",
            "экспорта и импорта", "таможенным органом", "вывозе и ввозе",
            "вэд", "валютному контролю", "импорт и экспорт",
        ),
        ("foreign_trade", "import", "export", "currency_control", "customs", "вэд", "импорт", "экспорт"),
        ("валютн", "внешнеторгов", "экспорт", "импорт", "таможенн", "вывоз", "ввоз"),
        40,
        60,
    ),
    DomainRule(
        "info_security_it",
        ("информационная безопасность", "информационные системы", "цифровые технологии", "идентификация пользователей"),
        (
            "информационной безопасности", "государственной информационной системе",
            "информационных технологиях", "цифровых технологий", "программного обеспечения",
            "информационно-телекоммуникационной сети", "информационных ресурсах",
        ),
        ("it_system", "info_security", "online_service", "messenger", "digital_platform", "saas"),
        ("информацион", "цифров", "программ", "сайт", "сети интернет", "электронн"),
        40,
        60,
    ),
)


NEUTRAL_DOMAIN = "neutral_no_match"
NEUTRAL_TOPICS = ("нейтральное регулирование", "no-match")
SUPPORTED_DOMAINS: tuple[str, ...] = tuple(
    rule.domain for rule in DOMAIN_RULES
) + (NEUTRAL_DOMAIN,)


def detect_domain(text: str) -> DomainRule | None:
    lower = text.casefold().replace("ё", "е")
    for rule in DOMAIN_RULES:
        if any(marker.casefold().replace("ё", "е") in lower for marker in rule.document_markers):
            return rule
    return None


def get_domain_rule(domain: str | None) -> DomainRule | None:
    return next((rule for rule in DOMAIN_RULES if rule.domain == domain), None)


def has_domain_client_marker(domain: str | None, keywords: list[str]) -> bool:
    rule = get_domain_rule(domain)
    if rule is None:
        return False
    joined = " ".join(keywords).casefold()
    return any(marker.casefold() in joined for marker in rule.client_markers)
