from dataclasses import dataclass

from .clients import SeedClient, SEED_CLIENTS
from .analyzer import AnalysisResult, RULES


@dataclass
class MatchedClient:
    client: SeedClient
    match_reason: str


@dataclass
class Notification:
    client_name: str
    message: str


def _get_rule_keywords(category: str) -> list[str] | None:
    """Вернуть keywords правила, соответствующего категории."""
    for rule in RULES:
        if rule["category"] == category:
            return rule["keywords"]
    return None


def match_clients(event: AnalysisResult) -> list[MatchedClient]:
    """Сопоставить регуляторное событие с seed-клиентами.

    Клиент считается затронутым, если keywords клиента пересекаются
    с любым из ключевых слов правила, определившего категорию события.
    """
    triggers = _get_rule_keywords(event.category)

    if triggers is None:
        # общее регулирование — затрагивает всех
        return [
            MatchedClient(
                client=c,
                match_reason=f"{c.segment} подпадает под общее регулирование",
            )
            for c in SEED_CLIENTS
        ]

    matched: list[MatchedClient] = []
    for c in SEED_CLIENTS:
        if any(t in kw.lower() for t in triggers for kw in c.keywords):
            matched.append(
                MatchedClient(
                    client=c,
                    match_reason=f"{c.segment} — keywords пересекаются с категорией \"{event.category}\"",
                )
            )

    return matched


def generate_notifications(
    matched_clients: list[MatchedClient], event: AnalysisResult
) -> list[Notification]:
    """Сгенерировать уведомления для затронутых клиентов."""
    notifications: list[Notification] = []
    for mc in matched_clients:
        msg = (
            f"Новое регулирование \"{event.title}\" "
            f"(категория: {event.category}, impact: {event.impact}) "
            f"может повлиять на ваш бизнес. Причина: {mc.match_reason}."
        )
        notifications.append(
            Notification(client_name=mc.client.name, message=msg)
        )
    return notifications
