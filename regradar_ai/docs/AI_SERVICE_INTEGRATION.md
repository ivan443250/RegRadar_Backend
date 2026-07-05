# RegRadar AI Service Integration

`RegRadarAIService` — стабильная backend-facing точка входа в AI-модуль.
Внешнему backend-коду не нужно импортировать LLM providers, rule engines,
RAG retrieval или JSONL repositories напрямую: orchestration и безопасные
fallback-сценарии скрыты за facade.

Внешний production backend не импортирует facade как Python-библиотеку: он
вызывает `POST /analyze`. Facade является внутренней границей FastAPI AI-service
и скрывает providers, engines, persistence и fallback от HTTP-контракта.

## Подключение

Для FastAPI используйте dependency из factory:

```python
from fastapi import Depends

from app.ai.reg_radar_ai_service import (
    FullAnalysisInput,
    RegRadarAIService,
)
from app.ai.service_factory import get_reg_radar_ai_service


async def analyze(
    text: str,
    service: RegRadarAIService = Depends(get_reg_radar_ai_service),
):
    return await service.run_full_analysis(
        FullAnalysisInput(
            text=text,
            document_id="document-42",
            version_id="v1",
            request_id="request-42",
        )
    )
```

В коде без FastAPI создайте отдельный экземпляр:

```python
from app.ai.service_factory import build_reg_radar_ai_service

service = build_reg_radar_ai_service()
```

`get_reg_radar_ai_service()` возвращает process-local singleton.
`build_reg_radar_ai_service()` возвращает новый экземпляр и подходит для тестов
или явного dependency injection. Factory не выполняет LLM-вызовы при создании.

## Идентификаторы, клиенты и модель

- Передавайте стабильные `document_id` и `version_id`, чтобы последующий RAG и
  storage API обращались к той же версии документа. Если `document_id` не задан
  для text flow, facade создаёт детерминированный ID из текста.
- `client_profiles` передаются в `FullAnalysisInput` или
  `CreateEventCardInput`. Непустой список заменяет demo seed portfolio только в
  рамках запроса; источник отражается в `client_profiles_source`.
- `model_override` должен входить в backend allowlist. Без override применяется
  модель из env. В mock mode выбор не приводит к внешнему вызову.
- `request_id` проходит через analysis/audit metadata и позволяет связать
  внешний запрос с `llm_call_ids`.

## Публичные операции

| Метод | Input DTO | Результат |
|---|---|---|
| `analyze_document()` | `AnalyzeDocumentInput` | `DocumentAnalysis` |
| `run_full_analysis()` | `FullAnalysisInput` | `FullAIAnalysisResponse` |
| `create_event_card()` | `CreateEventCardInput` | `RegulatoryEventCard` |
| `create_event_card_from_document()` | `CreateEventCardFromDocumentRequest` | `CreateEventCardFromDocumentResponse` |
| `ask_rag()` | `RagAskInput` | `RagAnswer` |
| `create_notifications()` | `CreateNotificationsInput` | `list[NotificationDraft]` |
| `mock_send_notification()` | `MockSendNotificationInput` | `NotificationMockSendResponse` |
| `get_models()` | — | `AIModelsResponse` |
| `healthcheck()` | — | безопасный status/config/storage/prompt report |

Все операции с анализом асинхронные. `get_models()` и `healthcheck()` синхронные
и не обращаются к платному или внешнему LLM API.

## Границы ответственности

Facade выполняет:

- выбор настроенного LLM Gateway и controlled fallback;
- полный pipeline анализа, EventCard и RAG;
- привязку `document_id`, `version_id`, `request_id` и chunk evidence;
- persistence документов, chunks, событий, RAG history и mock delivery;
- notification safety checks и disclaimer;
- формирование metadata о provider, fallback, audit и storage.

HTTP-слой по-прежнему отвечает за transport concerns: multipart upload,
ограничение размера файла, TXT/PDF extraction и преобразование HTTP errors.
Facade не выполняет OCR, реальную доставку уведомлений и не передаёт LLM
решения по impact, client matching или review state.

LLM используется только для `DocumentAnalysis` и grounded RAG answer. Impact,
domain normalization, client matching, notification drafts, EventCard и review
state остаются controlled baseline.

## Metadata

У результатов анализа и EventCard проверяйте `analysis_metadata`:

- `request_id` и `llm_call_ids` связывают продуктовый запрос с audit trail;
- `provider`, `runtime`, `selected_model`, `model_version`, `prompt_version`
  описывают фактический runtime;
- `fallback_used`, `fallback_reason`, `warnings` объясняют degraded result;
- `client_profiles_source` различает request portfolio и `seed_fallback`;
- `document_saved`, `chunks_saved`, `event_saved`, `rag_chat_saved` отражают
  состояние persistence.

Mock-send дополнительно возвращает `saved` и
`metadata.notification_saved`. Полезный analysis response остаётся доступен,
даже если локальное сохранение завершилось warning.

## Ошибки и degraded mode

- Ошибки модели/провайдера, допускающие безопасное восстановление, переходят в
  controlled baseline и отражаются в `analysis_metadata.fallback_used`,
  `fallback_reason` и `warnings`.
- Ошибка JSONL storage не уничтожает полезный результат анализа: соответствующие
  `*_saved` остаются `false`, а warning попадает в metadata.
- Ошибки входных данных facade представлены `AIServiceValidationError`.
  FastAPI adapter переводит их в HTTP 400 с понятными `message` и `errors`.
- RAG для неизвестного документа или нерелевантного вопроса возвращает
  `no_data=true` и не вызывает LLM.

## Healthcheck

```http
GET /api/ai/health
```

Endpoint проверяет конфигурацию provider mode, каталог разрешённых моделей,
доступность путей persistence и наличие prompt-файлов. Он намеренно не делает
тестовый LLM-запрос, поэтому безопасен для readiness-проверок и не расходует
внешний API budget.

## Тестовая подмена

FastAPI dependency можно заменить без patch внутренних provider-классов:

```python
app.dependency_overrides[get_reg_radar_ai_service] = lambda: fake_service
```

Для сброса кешированного singleton в тестах доступен
`reset_reg_radar_ai_service_for_tests()`.

Текущие repositories используют append-only JSONL. Production backend может
передать через `build_reg_radar_ai_service(...)` совместимые repository adapters
для PostgreSQL, не меняя внешний service contract. Транзакционную семантику и
миграции при такой замене определяет инфраструктурный слой production backend.

## Правило интеграции

Новый backend-код должен зависеть от `RegRadarAIService` и его DTO. Прямые
импорты `PolzaAIProvider`, `MockLLMProvider`, impact/matching engines и storage
repositories допустимы только внутри реализации AI-модуля, инфраструктурных
debug endpoint'ов и их unit-тестов.
