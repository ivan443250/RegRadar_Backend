# RegRadar AI Module Pipeline & Integration Contract v1.4

## 1. Текущее состояние

RegRadar — работающий demo/MVP для анализа регуляторных документов банка.
Система поддерживает TXT/PDF upload, optional PolzaAI, controlled baseline,
RegulatoryEventCard, evidence, RAG-lite, LLM audit, JSONL persistence и
безопасную mock-доставку уведомлений.

Главный продуктовый принцип:

```text
LLM извлекает DocumentAnalysis и формирует grounded RAG answer.
Impact, domain normalization, client matching, notifications и review
остаются детерминированным controlled baseline.
```

Текущее подтверждённое состояние:

* FastAPI HTTP AI-service для запуска отдельно или в Docker Compose;
* `mock`, `polza`, `polza_with_fallback`;
* language guard с одним retry и безопасным fallback;
* 11 baseline-доменов и защита `neutral_no_match`;
* TXT/PDF extraction до 10 MB, без OCR;
* evidence, связанные с `document_id/version_id/chunk_id`;
* keyword RAG-lite с citations и no-data режимом;
* append-only LLM audit trail;
* persistence-lite repository layer на JSONL;
* mock notification delivery с safety gate;
* обязательный human review для EventCard;
* стабильный backend-facing facade `RegRadarAIService`;
* отдельный compatibility layer для основного `.NET RegRadar.Api`;
* production compatibility contract `POST /analyze`, `GET /health`;
* 326 pytest-тестов без реальных внешних HTTP-вызовов;
* real-doc evaluation: 39/39 enabled документов проходят.

## 2. Полный pipeline

```text
TXT/PDF или text/chunks
→ extraction и clean_eval_metadata
→ deterministic chunking
→ RegRadarAIService facade
→ prompt_loader
→ LLMGateway
   ├─ MockLLMProvider
   └─ PolzaAIProvider
→ DocumentAnalysis
→ language guard / retry / fallback
→ baseline domain + evidence normalization
→ ImpactAssessment
→ ClientRelevance[]
→ NotificationDraft[]
→ RegulatoryEventCard
→ JSONL persistence
→ RAG-lite по chunks/evidence
→ notification mock-send
→ review workflow
```

LLM не принимает решения о final impact, client relevance, notification
recipient или review state.

## 3. Ответственность модулей

Архитектурная граница текущей версии:

```text
FastAPI routes / внешний backend
→ RegRadarAIService (typed DTO + orchestration)
→ document analysis / controlled baseline / RAG services
→ LLM Gateway + replaceable repositories + audit
```

Межсервисный путь не раскрывает AI internals:

```text
RegRadar.Api
→ POST /analyze (production) или extended /api/integration/...
→ BackendContractService / MainBackendIntegrationService
→ RegRadarAIService
→ structured result для сохранения в main backend
```

Integration layer не пишет в БД RegRadar.Api и не владеет его бизнес-сущностями.
Полный контракт: [MAIN_BACKEND_INTEGRATION.md](MAIN_BACKEND_INTEGRATION.md).

AI-слой отвечает за:

* структурированный `DocumentAnalysis`;
* controlled normalization и evidence validation;
* explainable `ImpactAssessment`;
* сопоставление только релевантных клиентов;
* безопасные `NotificationDraft`;
* сборку `RegulatoryEventCard`;
* source-grounded RAG answer.

Backend boundary отвечает за:

* upload и проверку типа/размера файла;
* TXT/PDF extraction и chunking;
* вызов AI-сервисов;
* JSONL persistence и debug endpoints;
* LLM audit;
* notification mock delivery.

Публичной точкой интеграции backend-кода с AI-модулем является
`RegRadarAIService`. FastAPI routes получают facade через dependency factory и
не выбирают provider, baseline engine или repository самостоятельно. Multipart
parsing и TXT/PDF extraction остаются transport-ответственностью routes.

Система не выполняет:

* OCR и web scraping;
* реальную email/SMS/webhook/Bitrix доставку;
* автоматическую публикацию результата клиенту;
* PostgreSQL/Redis/pgvector persistence;
* юридическую консультацию или создание официальных документов.

## 4. API surface

### Анализ и карточки

```text
GET  /health
POST /analyze
GET  /api/ai/health
GET  /api/ai/models
POST /api/analyze
POST /api/ai/document-analysis
POST /api/ai/full-analysis
POST /api/ai/gateway-test
POST /api/events/create-card
POST /api/events/create-card-from-document
POST /api/documents/upload-analysis
POST /api/documents/upload-create-card
POST /api/integration/main-backend/analyze-document
GET  /api/integration/main-backend/client-profiles
GET  /api/integration/main-backend/health
```

### RAG и notification delivery

```text
POST /api/rag/ask
POST /api/notifications/mock-send
```

### Dev/demo observability

```text
GET /api/debug/llm-calls?limit=50
GET /api/debug/documents?limit=50
GET /api/debug/documents/{document_id}/chunks?version_id=v1
GET /api/debug/events?limit=50
GET /api/debug/rag-chats?document_id=...&limit=20
GET /api/debug/notifications?limit=50
GET /api/debug/notifications/by-document/{document_id}?version_id=v1
GET /api/debug/notifications/by-client/{client_id}?limit=50
```

Debug endpoints предназначены только для локального demo/dev. В production их
нужно закрыть авторизацией или отключить.

## 5. Основные flows

### Full analysis

```text
POST /api/ai/full-analysis
text + optional client_profiles + optional model_override
→ FullAIAnalysisResponse
→ сохранить DocumentRecord + ChunkRecord[]
```

Непустой `client_profiles` полностью заменяет seed portfolio. При отсутствии
профилей используется `seed_fallback`, что явно отражается в metadata.

### Upload analysis

```text
POST /api/documents/upload-analysis
multipart TXT/PDF
→ extract text
→ full_ai_analysis
→ persist document/chunks
→ UploadAnalysisResponse
```

### Upload card

```text
POST /api/documents/upload-create-card
multipart TXT/PDF + optional document metadata/client profiles
→ extraction
→ chunks
→ full analysis
→ RegulatoryEventCard(needs_review)
→ persist document/chunks/event
```

### Card from document contract

```text
POST /api/events/create-card-from-document
DocumentMetadataForAI + DocumentChunkForAI[] + ClientProfileForAI[]
→ sort chunks
→ analyze once
→ link evidence to chunks
→ persist document/chunks/event
```

Request `title` имеет приоритет над `DocumentAnalysis.title`; filename
используется только как upload fallback.

## 6. LLM Gateway

```text
AI service
→ LLMGateway.generate_structured()
→ ProviderRouter
   ├─ MockLLMProvider
   └─ PolzaAIProvider (OpenAI-compatible HTTP)
→ JSON extraction
→ Pydantic validation
```

`RegRadarAIService` расположен выше Gateway и controlled baseline. Он сохраняет
стабильный контракт для другого backend-кода, а внутренние providers и engines
могут развиваться без изменения вызывающей стороны. Factory и DTO описаны в
[AI_SERVICE_INTEGRATION.md](AI_SERVICE_INTEGRATION.md).

Поддерживаемые режимы:

* `LLM_PROVIDER=mock` — полностью локальный baseline;
* `LLM_PROVIDER=polza` — PolzaAI с продуктовым safe fallback;
* `LLM_PROVIDER=polza_with_fallback` — тот же provider с явно обозначенным
  fallback-режимом.

Основные переменные:

```env
LLM_PROVIDER=mock
LLM_MODEL=mock-reg-radar-v1
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2

POLZA_API_KEY=
POLZA_BASE_URL=https://polza.ai/api/v1
POLZA_MODEL=deepseek/deepseek-v4-flash
POLZA_ALLOWED_MODELS=deepseek/deepseek-v4-flash,openai/gpt-4o,qwen/qwen3.6-plus,qwen/qwen3.5-flash-02-23
POLZA_TIMEOUT_SECONDS=60
POLZA_MAX_RETRIES=2
```

Приложение читает environment процесса. Для загрузки корневого `.env` сервер
нужно запускать с `--env-file .env`.

Typed errors:

```text
LLMGatewayError
├── LLMProviderConfigError
├── LLMProviderUnavailableError
│   └── LLMProviderTimeoutError
├── LLMResponseParsingError
├── LLMResponseValidationError
└── LLMResponseLanguageError
```

При безопасной ошибке DocumentAnalysis формируется controlled mock baseline;
`fallback_used`, `fallback_reason`, warnings и audit call IDs сохраняются.

## 7. Prompt и language contract

Активные prompts:

```text
app/ai/prompts/document_analysis_v1.md
app/ai/prompts/rag_answer_v1.md
```

`prompt_loader` использует `string.Template`, не выполняет prompt как код и
возвращает typed errors для отсутствующих файлов/переменных.

DocumentAnalysis должен возвращать пользовательские поля на русском языке.
`source_fragments` остаются дословными фрагментами исходного документа. Если
PolzaAI возвращает преимущественно английский текст:

```text
validation warning
→ один language retry
→ повторная validation
→ controlled mock fallback при повторной ошибке
```

## 8. Controlled baseline

Поддерживаемые домены:

```text
personal_data
aml
foreign_trade_currency_control
financial_market_securities
fuel_excise
tax_reporting
payments_digital_ruble
lending_consumer_credit
info_security_it
product_marking_trade
neutral_no_match
```

Baseline контролирует:

* domain/topic normalization;
* verbatim evidence;
* impact score, level, urgency и reasoning;
* client matching по профилю/tags;
* notification recipients;
* neutral/no-match safety.

Для неизвестного или нейтрального документа:

```text
client_relevance = []
notification_drafts = []
review_state = needs_review
```

Массового fallback «всем клиентам relevance=50» нет.

## 9. Core contracts

Основная цепочка Pydantic-схем:

```text
DocumentAnalysis
→ ImpactAssessment
→ ClientRelevance[]
→ NotificationDraft[]
→ RegulatoryEventCard
```

`RegulatoryEventCard` содержит:

* document analysis и impact assessment;
* affected clients и notification drafts;
* structured `EvidenceFragment[]`;
* source set, confidence и no-data reason;
* `review_state`, `review_required`;
* model/prompt/provider metadata.

`AnalysisMetadata` содержит:

```text
analysis_provider / provider / runtime
model_version / selected_model / prompt_version
processing_mode
fallback_used / fallback_reason / warnings
client_profiles_source
request_id / llm_call_ids / latency_ms
context_document_id / context_version_id
document_saved / chunks_saved / event_saved / rag_chat_saved / notification_saved
storage_source
```

## 10. Evidence contract

```python
class EvidenceFragment(BaseModel):
    fragment_id: str
    text: str
    source_type: str
    document_id: str | None
    version_id: str | None
    chunk_id: str | None
    source_url: str | None
    evidence_role: str
```

Правила:

1. Evidence является дословным фрагментом очищенного source text.
2. Eval annotation header удаляется до chunking и evidence extraction.
3. Document/version IDs ставятся integration/upload flow.
4. `chunk_id` ставится только при реальной связи с chunk.
5. Отсутствующий или непривязанный evidence требует review.
6. LLM не может подменять или переводить source fragments.

## 11. RAG-lite

`POST /api/rag/ask` использует следующий приоритет контекста:

```text
request source_fragments/chunks
→ persisted chunks по document_id/version_id
→ process-local in-memory context fallback
→ no_data
```

Retrieval выполняется до LLM и основан на нормализованных токенах/ключевых
терминах. Фрагменты с недостаточным score отбрасываются. При отсутствии
релевантного контекста LLM не вызывается:

```json
{
  "answer": "Нет данных в базе по этому вопросу.",
  "no_data": true,
  "source_fragments": []
}
```

Ответ содержит citations с `document_id/version_id/chunk_id/score`. Технические
ID запрещены в пользовательском `answer` и показываются только в Sources.
Поддерживаются аудитории `bank_employee` и `client`.

Каждый exchange, включая no-data, сохраняется в `rag_chats.jsonl`. История пока
не подмешивается в multi-turn prompt.

## 12. LLM audit trail

Все Gateway-вызовы, language retry, fallback и RAG skipped записываются в:

```text
data/logs/llm_calls.jsonl
```

Audit record включает call/request IDs, endpoint, operation, provider/runtime,
model, prompt version, status, latency, размеры input/output, fallback/error и
safe metadata.

Не сохраняются:

* API key, Authorization/Bearer, client secret;
* полный prompt;
* полный исходный документ;
* RAG chunks/source fragments.

Запись append-only, `ensure_ascii=false`, защищена process-local lock. Ошибка
записи audit не ломает основной pipeline.

## 13. Persistence-lite

Repository boundary находится в `app/storage/`:

```text
jsonl_repository.py
document_repository.py
event_repository.py
rag_chat_repository.py
notification_repository.py
persistence_service.py
```

Runtime files:

```text
data/storage/documents.jsonl
data/storage/chunks.jsonl
data/storage/events.jsonl
data/storage/rag_chats.jsonl
data/storage/notifications.jsonl
```

`documents.jsonl` хранит metadata/hash/length/chunks_count, но не полный текст.
Текст сохраняется только в chunks для RAG. Репозитории используют append-only
JSONL; latest/deduplication выполняются при чтении. Storage error не меняет AI
результат и добавляет `persistence warning`.

Это replaceable MVP boundary. Production repository может использовать
PostgreSQL/pgvector без переноса storage-логики в AI-модуль.

## 14. Notification workflow

```text
ClientRelevance
→ NotificationDraft
→ safety validation
→ POST /api/notifications/mock-send
→ sent_mock
→ notifications.jsonl
```

NotificationDraft получает notification/client/document/version context,
source chunk IDs и disclaimer.

Перед mock-send проверяются:

* обязательные title/short/full message и disclaimer;
* совпадение request/draft client ID;
* client relevance по сохранённому DocumentRecord/EventCard;
* запрет `neutral_no_match`;
* отсутствие категоричных/юридических формулировок.

Mock-send не вызывает внешние API. Storage failure возвращает `saved=false`, но
не превращает успешную demo-имитацию в HTTP 500. Seed clients относятся только
к standalone/debug flows; production `/analyze` отключает seed fallback.

## 15. Review contract

Новая EventCard создаётся так:

```text
review_state = needs_review
review_required = true
```

Ни PolzaAI, ни baseline, ни mock-send не переводят карточку в approved и не
публикуют её клиенту. Mock delivery демонстрирует технический workflow, а не
заменяет банковский approval.

## 16. Production HTTP boundary

Основной `.NET` backend вызывает только:

```text
GET  /health
POST /analyze
```

`/analyze` использует `BackendContractService → RegRadarAIService`, принимает
готовые chunks/client profiles и возвращает минимальный structured response.
Standalone RAG, upload, EventCard, JSONL debug и mock-send endpoints сохранены
как диагностические возможности, но не входят в production contract.

## 17. Тестирование и evaluation

```powershell
python -m pytest
python -m scripts.run_real_samples_eval
```

Текущее состояние:

```text
pytest: 326 passed
real documents: 39/39 OK
```

Тесты используют mock HTTP/tmp paths и не выполняют реальные PolzaAI или
delivery вызовы.

## 18. Запуск

```powershell
cd C:\Projects\GitHub\regradar\regradar_ai
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env
```

URLs:

```text
Backend:  http://127.0.0.1:8000
Swagger:  http://127.0.0.1:8000/docs
```

## 19. Ограничения и roadmap

Текущие ограничения:

* JSONL не заменяет транзакционную production DB;
* keyword retrieval не является semantic/vector search;
* нет OCR для scanned PDF;
* нет real delivery adapter;
* нет auth/RBAC для debug endpoints;
* нет multi-turn RAG memory в prompt;
* `/chat` и pgvector-backed RAG требуют отдельного согласованного контракта.

Следующие production boundaries:

```text
JSONL repositories → PostgreSQL
keyword retrieval → pgvector/hybrid retrieval
debug endpoints → authenticated observability
mock-send → approved delivery adapters
review flags → полноценный human approval workflow
```
