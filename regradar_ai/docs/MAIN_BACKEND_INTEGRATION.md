# Main Backend Integration

Этот слой связывает основной `.NET RegRadar.Api` с существующим FastAPI
AI-service, не раскрывая внутренние providers, engines и repositories.

```text
Main Backend / RegRadar.Api
→ FastAPI integration API
→ RegRadarAIService
→ LLM Gateway (optional PolzaAI) + controlled baseline
```

Основной backend владеет бизнес-сущностями и production persistence:
`Documents`, `RegulatoryEvents`, `ClientImpacts`, `Notifications`, `Sources`.
AI-service принимает текст и client profiles, возвращает structured result и не
пишет напрямую в БД RegRadar.Api.

## Endpoints AI-service

Основной production-контракт backend-команды:

```text
POST /analyze
GET  /health
```

Расширенные dev/integration endpoint'ы сохраняются для диагностики и более
полного payload:

```text
POST /api/integration/main-backend/analyze-document
GET  /api/integration/main-backend/client-profiles
GET  /api/integration/main-backend/health
```

`/analyze` и extended `analyze-document` могут вызвать LLM. Оба health endpoint'а
не делают платный LLM-вызов.
Standalone API (`/api/ai/full-analysis`, upload, RAG, mock-send) остаётся
независимым от `MAIN_BACKEND_URL`.

## Production contract: POST /analyze

Main backend вызывает AI container по адресу `http://ai:8000/analyze`.
Пример request: [backend_contract_analyze_request.json](examples/backend_contract_analyze_request.json).

```json
{
  "documentId": "document-guid-1",
  "title": "Требования к персональным данным",
  "text": "Полный нормализованный текст документа",
  "chunks": ["Готовый чанк 0", "Готовый чанк 1"],
  "clients": [
    {
      "clientId": "client-guid-42",
      "companyName": "ООО Персональные сервисы",
      "okved": "62.01",
      "industry": "IT",
      "size": "Medium",
      "hasForeignTrade": false,
      "usesOnlinePayments": true,
      "handlesPersonalData": true,
      "cashOperationsLevel": "Low",
      "riskProfile": "High",
      "bankSegment": "Средний бизнес"
    }
  ]
}
```

Если `chunks` непустой, AI-service сохраняет переданные границы и анализирует их
в указанном порядке. Иначе chunks строятся из `text`. `documentId`, `title` и
`clientId` сохраняются из request.

Сокращённый response:

```json
{
  "provider": "polza",
  "model": "deepseek/deepseek-v4-flash",
  "promptVersion": "document_analysis_v1",
  "analysis": {
    "title": "Требования к персональным данным",
    "short_summary": "...",
    "long_summary": "...",
    "regulator": "...",
    "document_type": "...",
    "topics": [],
    "affected_industries": [],
    "key_dates": [
      {"date": "2026-10-01", "meaning": "вступление в силу"}
    ],
    "obligations": [],
    "source_fragments": [],
    "confidence": 0.85
  },
  "impact": {
    "impact_score": 50,
    "impact_level": "medium",
    "reasoning": "...",
    "evidence_fragments": [],
    "urgency": "medium",
    "confidence": 0.85
  },
  "clientRelevances": [
    {
      "client_id": "client-guid-42",
      "relevance_score": 70,
      "relevance_level": "high",
      "matched_factors": [],
      "explanation_for_bank": "...",
      "explanation_for_client": "...",
      "evidence_fragments": []
    }
  ]
}
```

Особенности:

- `clients=[]` строго возвращает `clientRelevances=[]`; seed fallback отключён;
- endpoint не запускает RAG/chat или notification mock-send;
- provider/model/promptVersion берутся из metadata фактического анализа;
- `key_dates` содержит grounded ISO date/meaning objects или `null`, если дат в
  переданных chunks нет;
- response не содержит EventCard, notification drafts и другие большие поля;
- LLM temperature уже равна `0.0` в Gateway request;
- HTTP deadline по умолчанию — 120 секунд, настраивается через
  `BACKEND_CONTRACT_TIMEOUT_SECONDS`.

Ошибка имеет единый вид без stacktrace:

```json
{"error": "понятное описание"}
```

Пустой `text` возвращает HTTP 400. Deadline возвращает HTTP 504. Неожиданная
ошибка логируется внутри AI-service и возвращает безопасный HTTP 500.

## Production health: GET /health

```json
{
  "status": "ok",
  "service": "regradar-ai",
  "providerMode": "polza_with_fallback",
  "defaultModel": "deepseek/deepseek-v4-flash",
  "prompts": ["document_analysis_v1", "rag_answer_v1"],
  "storage": {
    "documents": "ok",
    "chunks": "ok",
    "events": "ok",
    "rag_chats": "ok",
    "notifications": "ok"
  }
}
```

Healthcheck возвращает HTTP 200 и проверяет config/prompts/storage без LLM call.

## Configuration

```env
MAIN_BACKEND_URL=http://localhost:8080
MAIN_BACKEND_TIMEOUT_SECONDS=30
MAIN_BACKEND_ALLOW_SEED_FALLBACK=false
BACKEND_CONTRACT_TIMEOUT_SECONDS=120
```

Варианты адреса:

- оба сервиса в общей backend Docker network:
  `MAIN_BACKEND_URL=http://api:8080`;
- main backend запущен на Windows host, AI-service в Docker Desktop:
  `MAIN_BACKEND_URL=http://host.docker.internal:8080`;
- оба сервиса локально: `MAIN_BACKEND_URL=http://localhost:8080`.

В репозитории есть Dockerfile AI-service. Общий compose остаётся у backend-команды.

`POLZA_API_KEY` хранится только в environment AI-service. Он не передаётся в
main backend, integration request/response или audit log.

Если `MAIN_BACKEND_URL` не задан, analyze endpoint работает с непустым
`clientProfiles` из request. По умолчанию отсутствие профилей является понятной
ошибкой, а не скрытым переходом на demo portfolio. Для локального demo это можно
явно изменить через `MAIN_BACKEND_ALLOW_SEED_FALLBACK=true`.

## Extended/debug request

Пример находится в
[main_backend_analyze_request.json](examples/main_backend_analyze_request.json).

```json
{
  "document": {
    "id": "doc-123",
    "title": "Изменения требований к персональным данным",
    "text": "Организации обязаны соблюдать требования к обработке персональных данных.",
    "originalUrl": "https://example.test/doc-123",
    "regulator": "Роскомнадзор",
    "documentType": 1,
    "publicationDate": "2026-07-01"
  },
  "clientProfiles": [
    {
      "id": "client-42",
      "companyName": "ООО Интернет-магазин",
      "okved": "47.91",
      "industry": "e-commerce",
      "size": 1,
      "hasForeignTrade": false,
      "usesOnlinePayments": true,
      "handlesPersonalData": true,
      "cashOperationsLevel": 0,
      "riskProfile": 1,
      "bankSegment": "SME"
    }
  ],
  "modelOverride": "deepseek/deepseek-v4-flash",
  "requestId": "request-123"
}
```

Вызов из PowerShell:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/integration/main-backend/analyze-document" `
  -H "Content-Type: application/json" `
  --data-binary "@docs/examples/main_backend_analyze_request.json"
```

Если `clientProfiles` отсутствует, integration service запрашивает
`GET /api/ClientProfiles` у настроенного main backend. Явный пустой список не
запускает сетевую загрузку и не включает demo seed: по умолчанию это HTTP 400.

## Extended/debug response

Сокращённая форма:

```json
{
  "documentId": "doc-123",
  "regulatoryEvent": {
    "documentId": "doc-123",
    "title": "Изменения требований к персональным данным",
    "summary": "...",
    "impactLevel": 1,
    "impactExplanation": "...",
    "effectiveDate": null,
    "status": 1,
    "tags": ["personal_data", "персональные данные"]
  },
  "clientImpacts": [
    {
      "regulatoryEventId": null,
      "clientProfileId": "client-42",
      "companyName": "ООО Интернет-магазин",
      "impactLevel": 2,
      "explanation": "..."
    }
  ],
  "notificationDrafts": [
    {
      "regulatoryEventId": null,
      "clientProfileId": "client-42",
      "payload": "{...NotificationDraft JSON...}",
      "channel": 0,
      "status": 0
    }
  ],
  "evidence": [],
  "ragContext": {
    "documentId": "doc-123",
    "versionId": "v1",
    "chunkIds": [],
    "sourceFragments": []
  },
  "aiMetadata": {
    "provider": "mock",
    "runtime": "MOCK",
    "request_id": "request-123",
    "llm_call_ids": []
  },
  "rawAiResult": {}
}
```

`regulatoryEventId` остаётся `null`, пока main backend не сохранит
RegulatoryEvent и не назначит свой ID. Integration endpoint намеренно ничего не
POST'ит обратно без согласованного create-result API.

## DTO mapping

| Main backend | AI-service | Правило |
|---|---|---|
| `ClientProfileDto` | `ClientProfileForAI` | camelCase fields, flags и domain tags |
| `RegulatoryEventCard` | `RegulatoryEventPayload` | title/summary, impact, review status, domain/topics |
| `ClientRelevance` | `ClientImpactPayload` | client ID/name, relevance level и explainability |
| `NotificationDraft` | `NotificationPayload` | полный draft сериализуется в JSON string |
| `EvidenceFragment[]` | `evidence`/`ragContext` | document/version/chunk linkage сохраняется |

Client tags дополнительно включают `foreign_trade`, `online_payments`,
`personal_data`, `cash_operations`, `bank_segment:<value>` и
`industry:<value>`.

## Enum compatibility

Финальный read-API отдаёт enum'ы строками. DTO принимает `str | int`, чтобы не
сломать совместимость с первоначальным OpenAPI. Production `/analyze` всегда
возвращает уровни строками: `low`, `medium`, `high`, `critical`.

Extended payload mappers пока сохраняют локальные integer values:

```text
ImpactLevel: low=0, medium=1, high=2, critical=3
EventStatus: draft=0, needs_review=1, approved=2, rejected=3
NotificationChannel: mock=0, email=1, bank_app=2, webhook=3
NotificationStatus: draft=0, sent_mock=1
```

Константы находятся в `integrations/main_backend/mappers.py`. Их необходимо
синхронизировать с enum definitions RegRadar.Api до production integration.

## Main backend read API

`MainBackendApiClient` поддерживает финальные read endpoint'ы:

```text
GET /api/documents/{id}
GET /api/documents/{id}/text
GET /api/documents/{id}/chunks
GET /api/clientprofiles
GET /api/regulatoryevents/{id}/impacts
GET /api/notifications
```

`get_document_text()` принимает как plain JSON string, так и объект с `text` или
`content`. `get_document_chunks()` валидирует DTO и сортирует chunks по
`chunkIndex`.

Main backend обычно сам передаёт text/chunks в production `/analyze`. Extended
`analyze_existing_document_id()` при отсутствии явного текста теперь загружает
его через `/api/documents/{id}/text`.

Прямое подключение AI-service к PostgreSQL/pgvector в текущем этапе не
добавлялось: `/analyze` не нуждается в embeddings. Pgvector-backed RAG и `/chat`
остаются отдельным этапом после согласования схемы таблиц и chat contract.

## Error behavior

- Пустой `document.text` → HTTP 400.
- Явный пустой `clientProfiles` без разрешённого seed fallback → HTTP 400.
- Main backend недоступен при загрузке profiles → HTTP 502.
- URL не настроен и request profiles отсутствуют → HTTP 503.
- Невалидный main backend JSON/schema → HTTP 502.
- Provider/LLM safe failures продолжают использовать существующий controlled
  fallback и отражаются в `aiMetadata`.
- Local AI persistence warning не уничтожает structured result.

## Health and debug

```powershell
curl.exe "http://127.0.0.1:8000/api/integration/main-backend/health"
curl.exe "http://127.0.0.1:8000/api/integration/main-backend/client-profiles"
```

Health возвращает configured URL, reachability, AI-service health и notes. Для
reachability используется `GET /api/ClientProfiles`; платный LLM не вызывается.

## Ownership after analysis

Main backend отвечает за:

- создание/обновление `RegulatoryEvents`;
- сохранение `ClientImpacts` и `Notifications`;
- связь результата с `Documents`/`Sources`;
- production review, authorization и delivery workflow.

AI-service сохраняет только локальный audit/persistence-lite контекст для demo,
RAG и диагностики. Он не является владельцем основной бизнес-БД.

## Open questions for main backend

1. Какой endpoint принимает результат AI-анализа? В OpenAPI нет
   `POST /api/RegulatoryEvents`.
2. Должен ли `POST /api/Documents/{id}/reprocess` синхронно вызывать AI-service
   или ставить задачу в очередь?
3. Где main backend хранит evidence/source fragments и `aiMetadata`?
4. Каковы точные integer values для `ImpactLevel`, `EventStatus`,
   `NotificationChannel`, `NotificationStatus`, `ProcessingStatus` и
   `DocumentType`?
5. Нужно ли сохранять `rawAiResult`, и каковы лимиты размера/retention?
6. Должен ли main backend проксировать `/api/rag/ask` как будущий `/api/chat`?
7. Нужны ли service-to-service auth, correlation headers и idempotency key для
   integration endpoint?

## Verification

```powershell
python -m pytest
python -m scripts.run_real_samples_eval
```

## Docker

Сборка и локальный запуск:

```powershell
docker build -t regradar-ai .
docker run --rm -p 8000:8000 `
  -e LLM_PROVIDER=mock `
  -e BACKEND_CONTRACT_TIMEOUT_SECONDS=120 `
  --name regradar-ai regradar-ai
```

Фрагмент общего compose backend-команды:

```yaml
services:
  ai:
    build: ./path-to-regradar-ai
    environment:
      LLM_PROVIDER: polza_with_fallback
      POLZA_API_KEY: ${POLZA_API_KEY}
      POLZA_MODEL: deepseek/deepseek-v4-flash
      BACKEND_CONTRACT_TIMEOUT_SECONDS: 120
      MAIN_BACKEND_URL: http://api:8080
```

Main backend обращается к `http://ai:8000/analyze` и
`http://ai:8000/health`. `POLZA_API_KEY` передаётся только контейнеру `ai`.
`.dockerignore` исключает `.env` и runtime JSONL из build context.
