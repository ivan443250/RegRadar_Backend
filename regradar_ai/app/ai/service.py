import logging
import inspect
from uuid import uuid4

from .schemas import (
    AnalysisMetadata,
    ClientProfileForAI,
    DocumentAnalysis,
    ImpactAssessment,
    ClientRelevance,
    NotificationDraft,
    FullAIAnalysisResponse,
)
from .constants import (
    DEFAULT_ANALYSIS_PROVIDER,
    DEFAULT_MODEL_VERSION,
    DEFAULT_PROMPT_VERSION,
)
from .document_analysis_service import (
    analyze_document_with_gateway,
    get_last_gateway_execution,
    reset_last_gateway_execution,
)
from .gateway.config import get_config
from .gateway.errors import (
    LLMProviderConfigError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
    LLMResponseParsingError,
    LLMResponseLanguageError,
    LLMResponseValidationError,
)
from .mock_provider import analyze_document as analyze_document_legacy
from .impact_engine import assess_impact
from .financial_market_rules import (
    has_financial_client_marker,
    is_financial_market_topic,
)
from .fuel_excise_rules import (
    has_fuel_client_marker,
    is_fuel_excise_topic,
)
from .domain_rules import get_domain_rule, has_domain_client_marker
from .prompt_loader import PromptNotFoundError, PromptRenderError
from .model_catalog import resolve_model_selection
from .llm_call_logger import LLMCallLogRecord, estimate_tokens, log_llm_call

# Импортируем seed-клиентов из существующего сервиса
from ..services.clients import SEED_CLIENTS


logger = logging.getLogger(__name__)

SAFE_FALLBACK_ERRORS = (
    LLMProviderConfigError,
    LLMProviderUnavailableError,
    LLMProviderTimeoutError,
    LLMResponseParsingError,
    LLMResponseLanguageError,
    LLMResponseValidationError,
    PromptNotFoundError,
    PromptRenderError,
)


def _run_document_gateway(
    text: str,
    model_override: str | None,
    request_id: str,
    endpoint: str | None,
) -> DocumentAnalysis:
    """Call the enriched API while preserving simple test/provider adapters."""
    parameters = inspect.signature(analyze_document_with_gateway).parameters
    args = [text]
    if model_override:
        args.append(model_override)
    kwargs = {}
    if "request_id" in parameters:
        kwargs["request_id"] = request_id
    if "endpoint" in parameters:
        kwargs["endpoint"] = endpoint
    return analyze_document_with_gateway(*args, **kwargs)


DISCLAIMER = (
    "Это информационное уведомление и не является юридической рекомендацией. "
    "Для принятия решений обратитесь к квалифицированному юристу."
)


# --- Маппинг тем на человеческие описания для клиентов ---

TOPIC_CLIENT_FRIENDLY: dict[str, str] = {
    "персональные данные": "работает с персональными данными клиентов",
    "115-ФЗ / ПОД/ФТ": "проводит операции, подпадающие под требования ПОД/ФТ",
    "ВЭД": "ведёт внешнеэкономическую деятельность",
    "ценные бумаги": "участвует в операциях финансового рынка или выпуске ценных бумаг",
    "топливный рынок / акцизы": "связан с топливным рынком, нефтепереработкой или акцизами",
    "общее регулирование": "ведёт деятельность, подпадающую под общее регулирование",
}

TOPIC_EXPLANATION_BANK: dict[str, str] = {
    "персональные данные": "обрабатывает персональные данные покупателей, а документ касается требований 152-ФЗ",
    "115-ФЗ / ПОД/ФТ": "проводит операции, которые могут подпадать под требования ПОД/ФТ (115-ФЗ)",
    "ВЭД": "участвует во внешнеторговых операциях, а документ касается ВЭД",
    "ценные бумаги": "работает на рынке ценных бумаг, является эмитентом или участником организованной торговли",
    "топливный рынок / акцизы": "участвует в производстве, переработке, реализации или биржевой торговле нефтепродуктами",
    "общее регулирование": "деятельность клиента подпадает под общее регулирование",
}

TOPIC_EXPLANATION_CLIENT: dict[str, str] = {
    "персональные данные": "вы работаете с данными клиентов, и изменение может потребовать пересмотра процедур обработки",
    "115-ФЗ / ПОД/ФТ": "ваши операции могут потребовать дополнительных процедур идентификации",
    "ВЭД": "изменение может повлиять на ваши внешнеторговые операции",
    "ценные бумаги": "документ может быть релевантен, если ваша организация участвует в операциях с ценными бумагами, является эмитентом или связана с публичным обращением ценных бумаг",
    "топливный рынок / акцизы": "документ может быть релевантен организациям, связанным с нефтепродуктами и налоговым учётом акцизов",
    "общее регулирование": "изменение может затронуть общие аспекты вашей деятельности",
}


def _is_client_relevant(
    client_keywords: list[str], topics: list[str], domain: str | None = None
) -> bool:
    """Проверить, релевантен ли клиент хотя бы одной теме."""
    if domain:
        return has_domain_client_marker(domain, client_keywords)
    kw_lower = " ".join(client_keywords).lower()
    for topic in topics:
        topic_lower = topic.lower()
        if (
            "ценные бумаги" in topic_lower or "финансовый рынок" in topic_lower
        ) and has_financial_client_marker(client_keywords):
            return True
        if (
            "топливный рынок" in topic_lower
            or "нефтепереработка" in topic_lower
            or "акцизы" in topic_lower
        ) and has_fuel_client_marker(client_keywords):
            return True
        if "персональные данные" in topic_lower and ("персональные данные" in kw_lower or "152-фз" in kw_lower):
            return True
        if "115-фз" in topic_lower or "под/фт" in topic_lower:
            if "115-фз" in kw_lower or "под/фт" in kw_lower or "идентификация" in kw_lower:
                return True
        if "вэд" in topic_lower or "валютный контроль" in topic_lower:
            if "вэд" in kw_lower or "импорт" in kw_lower or "экспорт" in kw_lower:
                return True
    return False


def _relevance_score(
    client_keywords: list[str],
    topics: list[str],
    impact_level: str,
    domain: str | None = None,
) -> int:
    """Посчитать relevance_score для клиента."""
    base = 50
    kw_lower = " ".join(client_keywords).lower()

    if domain and has_domain_client_marker(domain, client_keywords):
        base += 25

    for topic in topics:
        topic_lower = topic.lower()
        if "персональные данные" in topic_lower and ("персональные данные" in kw_lower or "152-фз" in kw_lower):
            base += 25
        if ("115-фз" in topic_lower or "под/фт" in topic_lower) and ("115-фз" in kw_lower or "под/фт" in kw_lower or "идентификация" in kw_lower):
            base += 25
        if ("вэд" in topic_lower or "валютный контроль" in topic_lower) and ("вэд" in kw_lower or "импорт" in kw_lower or "экспорт" in kw_lower):
            base += 25
        if (
            "ценные бумаги" in topic_lower or "финансовый рынок" in topic_lower
        ) and has_financial_client_marker(client_keywords):
            base += 25
        if (
            "топливный рынок" in topic_lower
            or "нефтепереработка" in topic_lower
            or "акцизы" in topic_lower
        ) and has_fuel_client_marker(client_keywords):
            base += 25

    # Бонус от impact_level
    bonus = {"low": 0, "medium": 5, "high": 10, "critical": 15}
    base += bonus.get(impact_level, 0)

    return min(base, 100)


def _relevance_level(score: int) -> str:
    if score <= 40:
        return "low"
    elif score <= 70:
        return "medium"
    else:
        return "high"


def _priority_from_impact(impact_level: str) -> str:
    if impact_level == "critical":
        return "critical"
    elif impact_level == "high":
        return "high"
    elif impact_level == "medium":
        return "medium"
    else:
        return "low"


def _profile_keywords(profile: ClientProfileForAI) -> list[str]:
    """Преобразовать явные признаки профиля в keywords текущего matcher."""
    keywords = [
        value
        for value in (
            profile.okved,
            profile.industry,
            profile.size,
            profile.cash_operations_level,
            profile.risk_profile,
            profile.bank_segment,
        )
        if value
    ]
    if profile.handles_personal_data:
        keywords.extend(["персональные данные", "152-фз"])
    if profile.has_foreign_trade:
        keywords.extend(["вэд", "импорт", "экспорт"])
    if profile.uses_online_payments:
        keywords.extend(["онлайн", "платежи"])
    keywords.extend(profile.tags)
    cash_level = (profile.cash_operations_level or "").lower()
    risk_level = (profile.risk_profile or "").lower()
    if cash_level in {"medium", "high"} or risk_level == "high":
        keywords.extend(["наличные", "115-фз", "под/фт"])
    return keywords


def _matched_factors(
    document_analysis: DocumentAnalysis,
    keywords: list[str],
    profile: ClientProfileForAI | None,
) -> list[str]:
    """Вернуть только пересечение тем документа и признаков клиента."""
    topics_lower = " ".join(document_analysis.topics).lower()
    keywords_lower = " ".join(keywords).lower()
    factors: list[str] = []

    domain_rule = get_domain_rule(document_analysis.domain)
    if domain_rule and profile and profile.tags:
        matched_markers = [
            marker
            for marker in domain_rule.client_markers
            if marker.casefold() in keywords_lower
        ]
        if matched_markers:
            factors.append(
                f"Профильные признаки: {', '.join(matched_markers[:4])}"
            )

    if "персональные данные" in topics_lower:
        if "персональные данные" in keywords_lower or "152-фз" in keywords_lower:
            factors.append("Обработка персональных данных")
        if profile and profile.uses_online_payments and profile.handles_personal_data:
            factors.append("Онлайн-платежи с использованием клиентских данных")

    if "115-фз" in topics_lower or "под/фт" in topics_lower:
        if profile:
            cash_level = (profile.cash_operations_level or "").lower()
            risk_level = (profile.risk_profile or "").lower()
            if cash_level in {"medium", "high"}:
                factors.append(f"Наличные операции: {cash_level}")
            if risk_level == "high":
                factors.append("Повышенный risk_profile")
            if "идентификация" in keywords_lower:
                factors.append("Идентификация клиентов")
            if not factors and (
                "115-фз" in keywords_lower or "под/фт" in keywords_lower
            ):
                factors.append("Явный ПОД/ФТ-признак профиля")
        else:
            if "наличные" in keywords_lower:
                factors.append("Наличные операции")
            if "идентификация" in keywords_lower:
                factors.append("Идентификация клиентов")
            if not factors and (
                "115-фз" in keywords_lower or "под/фт" in keywords_lower
            ):
                factors.append("Операции, подпадающие под ПОД/ФТ")

    if "вэд" in topics_lower or "валютный контроль" in topics_lower:
        if any(value in keywords_lower for value in ("вэд", "импорт", "экспорт")):
            factors.append("ВЭД")
        if "импорт" in keywords_lower or "экспорт" in keywords_lower:
            factors.append("Импорт/экспорт")
        source_text = " ".join(document_analysis.source_fragments).lower()
        if "валютн" in source_text and "контрол" in source_text:
            factors.append("Валютный контроль")

    if is_financial_market_topic(document_analysis.topics):
        if any(value in keywords_lower for value in ("broker", "brokerage")):
            factors.append("Брокерская деятельность")
        if any(
            value in keywords_lower
            for value in ("issuer", "public_company")
        ):
            factors.append("Эмитент / публичная компания")
        if "exchange_trading" in keywords_lower:
            factors.append("Участник организованной торговли")
        if any(
            value in keywords_lower
            for value in (
                "securities",
                "securities_market",
                "investment",
                "investment_company",
                "financial_market",
                "strategic_enterprise",
            )
        ):
            factors.append("Рынок ценных бумаг / финансовый рынок")

    if is_fuel_excise_topic(document_analysis.topics):
        if any(
            value in keywords_lower
            for value in ("fuel", "fuel_trade", "oil_products", "petroleum")
        ):
            factors.append("Топливо / нефтепродукты")
        if "oil_processing" in keywords_lower:
            factors.append("Нефтепереработка")
        if "excise" in keywords_lower:
            factors.append("Акцизы")
        if "exchange_trading" in keywords_lower:
            factors.append("Биржевые торги")
        if any(value in keywords_lower for value in ("gas_station", "energy")):
            factors.append("Топливно-энергетический сектор")

    return list(dict.fromkeys(factors))


def match_clients(
    document_analysis: DocumentAnalysis,
    impact_assessment: ImpactAssessment,
    client_profiles: list[ClientProfileForAI] | None = None,
) -> list[ClientRelevance]:
    """Сопоставить документ с request-профилями или demo seed fallback."""
    candidates: list[
        tuple[str, str, str, list[str], ClientProfileForAI | None]
    ] = []
    if client_profiles:
        for profile in client_profiles:
            candidates.append(
                (
                    profile.client_id,
                    profile.company_name,
                    profile.industry
                    or profile.bank_segment
                    or profile.size
                    or "профиль клиента",
                    _profile_keywords(profile),
                    profile,
                )
            )
    else:
        candidates.extend(
            (
                f"seed-{index + 1}",
                client.name,
                client.segment,
                client.keywords,
                None,
            )
            for index, client in enumerate(SEED_CLIENTS)
        )

    matched_clients: list[ClientRelevance] = []
    for client_id, client_name, segment, keywords, profile in candidates:
        relevance_keywords = (
            profile.tags if profile and profile.tags else keywords
        )
        if not _is_client_relevant(
            relevance_keywords,
            document_analysis.topics,
            document_analysis.domain,
        ):
            continue

        score = _relevance_score(
            relevance_keywords,
            document_analysis.topics,
            impact_assessment.impact_level,
            document_analysis.domain,
        )
        level = _relevance_level(score)
        primary_topic = (
            document_analysis.topics[0]
            if document_analysis.topics
            else "общее регулирование"
        )
        explanation_bank = TOPIC_EXPLANATION_BANK.get(
            primary_topic,
            "подпадает под регулирование",
        )
        explanation_client = TOPIC_EXPLANATION_CLIENT.get(
            primary_topic,
            "изменение может быть важно для вашей компании",
        )

        matched_factors = _matched_factors(document_analysis, keywords, profile)
        if not matched_factors:
            continue

        matched_clients.append(
            ClientRelevance(
                client_id=client_id,
                client_name=client_name,
                relevance_score=score,
                relevance_level=level,
                matched_factors=matched_factors,
                explanation_for_bank=(
                    f"Клиент {client_name} ({segment}) релевантен, потому что "
                    f"{explanation_bank}. Основание профиля: "
                    f"{', '.join(matched_factors)}."
                ),
                explanation_for_client=f"{explanation_client}.",
                evidence_fragments=document_analysis.source_fragments[:2],
                recommended_notification_type=(
                    "email" if level != "high" else "push + email"
                ),
            )
        )

    return matched_clients


def full_ai_analysis(
    text: str,
    client_profiles: list[ClientProfileForAI] | None = None,
    model_override: str | None = None,
    request_id: str | None = None,
    endpoint: str | None = None,
    use_seed_fallback: bool = True,
) -> FullAIAnalysisResponse:
    """Полный AI-конвейер: анализ документа → impact → клиенты → уведомления.

    DocumentAnalysis проходит через LLM Gateway. Остальные этапы используют
    текущую rule-based/mock логику без реальной LLM.
    """
    config = get_config()
    model_selection = resolve_model_selection(model_override, config)
    provider_name = config.llm_provider.lower().strip()
    metadata_provider = "polza" if config.is_polza_mode else provider_name
    client_profiles_source = (
        "request"
        if client_profiles or not use_seed_fallback
        else "seed_fallback"
    )
    effective_request_id = request_id or str(uuid4())
    analysis_metadata = AnalysisMetadata(
        analysis_provider=metadata_provider,
        model_version=config.active_model,
        prompt_version=DEFAULT_PROMPT_VERSION,
        fallback_used=False,
        processing_mode=(
            "gateway_mock"
            if provider_name == DEFAULT_ANALYSIS_PROVIDER
            else "gateway_polza"
        ),
        client_profiles_source=client_profiles_source,
        selected_model=model_selection.selected_model,
        request_id=effective_request_id,
    )

    # Шаг 1: gateway-based DocumentAnalysis с безопасным legacy fallback
    reset_last_gateway_execution()
    try:
        doc = _run_document_gateway(
            text,
            model_selection.gateway_override,
            effective_request_id,
            endpoint,
        )
        execution = get_last_gateway_execution()
        if execution:
            analysis_metadata.model_version = execution.model
            analysis_metadata.warnings = list(execution.warnings)
            analysis_metadata.request_id = execution.request_id
            analysis_metadata.llm_call_ids = list(execution.call_ids)
            analysis_metadata.latency_ms = execution.latency_ms
    except SAFE_FALLBACK_ERRORS as error:
        logger.exception(
            "Gateway-based DocumentAnalysis failed; using legacy mock fallback: "
            "provider=%s error_type=%s error=%s",
            provider_name,
            type(error).__name__,
            error,
        )
        doc = analyze_document_legacy(text)
        is_polza_fallback = config.is_polza_mode
        warnings = ["Falling back to MockProvider"]
        failed_execution = get_last_gateway_execution()
        if failed_execution:
            warnings.extend(failed_execution.warnings)
        if is_polza_fallback and not config.polzaai_api_key:
            warnings.insert(0, "POLZA_API_KEY is not configured.")
        language_fallback = isinstance(error, LLMResponseLanguageError)
        fallback_record = LLMCallLogRecord(
            request_id=effective_request_id,
            endpoint=endpoint,
            operation="fallback",
            provider="mock",
            runtime="FALLBACK",
            model=DEFAULT_MODEL_VERSION,
            selected_model=model_selection.selected_model,
            prompt_version=DEFAULT_PROMPT_VERSION,
            status="fallback",
            input_chars=len(text),
            input_tokens_estimate=estimate_tokens(len(text)),
            fallback_used=True,
            fallback_reason=(
                "LLM returned non-Russian user-visible fields"
                if language_fallback
                else f"{type(error).__name__}: {error}"
            ),
            error_type=type(error).__name__,
            error_message=str(error),
            warnings=warnings,
            metadata={"reason": "safe_baseline_fallback"},
        )
        log_llm_call(fallback_record)
        failed_call_ids = (
            list(failed_execution.call_ids) if failed_execution else []
        )
        analysis_metadata = AnalysisMetadata(
            analysis_provider="polza" if is_polza_fallback else "legacy_mock",
            model_version=(
                model_selection.selected_model
                if is_polza_fallback
                else DEFAULT_MODEL_VERSION
            ),
            prompt_version=DEFAULT_PROMPT_VERSION,
            fallback_used=True,
            fallback_reason=(
                "LLM returned non-Russian user-visible fields"
                if language_fallback
                else f"PolzaAI request failed: {type(error).__name__}: {error}"
                if is_polza_fallback
                else f"{type(error).__name__}: {error}"
            ),
            processing_mode=(
                "gateway_polza_with_fallback"
                if is_polza_fallback
                else DEFAULT_ANALYSIS_PROVIDER
            ),
            client_profiles_source=client_profiles_source,
            warnings=(
                warnings
                if is_polza_fallback
                else ["Gateway failed; legacy mock fallback was used."]
            ),
            selected_model=model_selection.selected_model,
            request_id=effective_request_id,
            llm_call_ids=failed_call_ids + [fallback_record.call_id],
            latency_ms=(failed_execution.latency_ms if failed_execution else None),
        )

    # Шаг 2: ImpactAssessment
    impact = assess_impact(doc)

    # Шаг 3: ClientRelevance
    client_relevance = (
        match_clients(doc, impact, client_profiles)
        if client_profiles or use_seed_fallback
        else []
    )

    # Шаг 4: NotificationDrafts
    notifications: list[NotificationDraft] = []
    financial_market = is_financial_market_topic(doc.topics)
    fuel_excise = is_fuel_excise_topic(doc.topics)
    for cr in client_relevance:
        if fuel_excise:
            short_msg = (
                "Документ может быть релевантен, если ваша организация связана "
                "с производством, переработкой, реализацией или биржевыми "
                "торгами нефтепродуктами, а также с налоговым учётом акцизов."
            )
        elif financial_market:
            short_msg = (
                "Документ может быть релевантен, если ваша организация "
                "участвует в операциях с ценными бумагами, является эмитентом "
                "или связана с публичным обращением ценных бумаг."
            )
        else:
            short_msg = (
                f"Новое регулирование \"{doc.title}\" "
                f"(тема: {', '.join(doc.topics)}, влияние: {impact.impact_level}) "
                f"может быть релевантно для вас."
            )
        full_msg = (
            (f"{short_msg}\n\n" if financial_market or fuel_excise else "")
            + f"Документ: {doc.title}\n\n"
            f"Краткое содержание: {doc.short_summary}\n\n"
            f"Влияние: {impact.impact_level} (score: {impact.impact_score})\n"
            f"Обоснование: {impact.reasoning}\n\n"
            f"{DISCLAIMER}"
        )

        notifications.append(
            NotificationDraft(
                notification_id=str(uuid4()),
                client_id=cr.client_id,
                client_name=cr.client_name,
                title=f"Уведомление: {doc.title}",
                short_message=short_msg,
                full_message=full_msg,
                client_friendly_explanation=cr.explanation_for_client,
                source_link=None,
                disclaimer=DISCLAIMER,
                priority=_priority_from_impact(impact.impact_level),
                channel_payload={
                    "type": "email",
                    "to": f"{cr.client_name.lower().replace(' ', '_')}@example.com",
                },
            )
        )

    return FullAIAnalysisResponse(
        document_analysis=doc,
        impact_assessment=impact,
        client_relevance=client_relevance,
        notification_drafts=notifications,
        analysis_metadata=analysis_metadata,
    )
