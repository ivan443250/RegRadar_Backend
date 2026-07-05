# RegRadar Backend ↔ AI-модуль: интеграционная документация

Документ для разработчика AI-контура (LLM gateway / RAG / Impact Engine).
Backend готов и работает; здесь описано, что уже есть, как мы стыкуемся и что нужно от твоей части.

## 1. Что уже есть со стороны backend

Стек: ASP.NET Core (.NET 10) + PostgreSQL (образ с **pgvector**) + Redis + фоновый воркер. Всё поднимается `docker compose up --build`.

Реализованный контур (твой «deterministic layer» из ТЗ — уже готов у меня):

| Из твоего ТЗ (deterministic) | Реализация в backend |
|---|---|
| hash, dedup | SHA-256 нормализованного текста, уникальные индексы БД |
| metadata | Document: source, original_url, regulator, publication_date, document_type, статусы |
| chunks | нарезка со скользящим окном (1000 символов, overlap 100), таблица `DocumentChunks` |
| keyword/rule signals | rule-based impact assessor (regex-факторы × флаги клиента) — работает как fallback, замещается твоим скорингом |
| source priority | источники: RSS Банка России, ручная загрузка, seed-файлы |
| status | ProcessingStatus per-document + журнал ProcessingJobs |

Каждый AI-вызов логируется в таблицу `LLMCallLogs`: provider, model, prompt version, input size, output, status, error, latency — со стороны backend это уже автоматика, тебе достаточно отдавать метаданные (см. §3).

## 2. Архитектура стыковки

Твой модуль — **отдельный HTTP-сервис в отдельном контейнере** в общем docker-compose. Рекомендуемая форма поставки: папка `ai/` в этом репозитории (исходники + Dockerfile), сервис `ai` в compose.

Сеть compose: контейнеры видят друг друга по именам сервисов.

```
backend (api, worker)  ──HTTP──►  ai:8000        (анализ документов)
ai                     ──HTTP──►  api:8080       (чтение данных для RAG)
ai                     ──TCP───►  postgres:5432  (свои таблицы эмбеддингов, pgvector уже установлен)
браузер/фронт          ──HTTP──►  localhost:8080 (backend), чат — см. §6
```

Наружу твой сервис порт не публикует — его единственные клиенты внутри сети.

## 3. Главный контракт: что backend вызывает у тебя

Backend в пайплайне обработки документа делает **один синхронный вызов**:

```
POST http://ai:8000/analyze
Content-Type: application/json
```

Запрос:

```json
{
  "documentId": "guid",
  "title": "Изменения в 115-ФЗ...",
  "text": "полный нормализованный текст документа",
  "chunks": ["чанк 0", "чанк 1", "..."],
  "clients": [
    {
      "clientId": "guid",
      "companyName": "ИмпортТрейд",
      "okved": "46.69",
      "industry": "Оптовая торговля, ВЭД",
      "size": "Medium",
      "hasForeignTrade": true,
      "usesOnlinePayments": false,
      "handlesPersonalData": false,
      "cashOperationsLevel": "Medium",
      "riskProfile": "High",
      "bankSegment": "Средний бизнес"
    }
  ]
}
```

Ответ — твои схемы из ТЗ (DocumentAnalysis + ImpactAssessment + ClientRelevance), собранные в один объект:

```json
{
  "provider": "polza",
  "model": "название-модели",
  "promptVersion": "document_analysis@v2",

  "analysis": {
    "title": "...",
    "short_summary": "...",
    "long_summary": "...",
    "regulator": "Банк России",
    "document_type": "...",
    "topics": ["115-ФЗ", "наличные"],
    "affected_industries": ["..."],
    "key_dates": [{ "date": "2026-10-01", "meaning": "вступление в силу" }],
    "obligations": ["..."],
    "source_fragments": ["..."],
    "confidence": 0.87
  },

  "impact": {
    "impact_score": 72,
    "impact_level": "high",
    "reasoning": "...",
    "evidence_fragments": ["..."],
    "urgency": "...",
    "confidence": 0.8
  },

  "clientRelevances": [
    {
      "client_id": "guid из запроса",
      "relevance_score": 85,
      "relevance_level": "high",
      "matched_factors": ["foreign_trade"],
      "explanation_for_bank": "...",
      "explanation_for_client": "...",
      "evidence_fragments": ["..."]
    }
  ]
}
```

Как backend использует ответ (тебе полезно знать, что критично):

| Поле ответа | Куда идёт |
|---|---|
| `analysis.title`, `short_summary` | карточка RegulatoryEvent (title, summary) |
| `impact.impact_level` + `reasoning` | ImpactLevel + ImpactExplanation карточки |
| `analysis.key_dates` (вступление в силу) | EffectiveDate |
| `analysis.topics` | Tags |
| `clientRelevances[]` | записи ClientImpact (кто затронут и почему) |
| `provider`, `model`, `promptVersion` | LLMCallLog (обязательно!) |
| весь ответ целиком | LLMCallLog.Output (аудит) |

**Маппинг уровней:** у backend enum `Low | Medium | High`. Твои `low/medium/high/critical` маппятся так: critical → High (score сохраняется в объяснении). Если решим показывать critical отдельно — скажи, я добавлю значение в enum, это одна миграция-безболезненная правка.

**Жёсткие требования к контракту:**
- `impact_level`/`relevance_level` — только значения из твоей шкалы, ровно строками;
- даты: если в документе нет — `null`, не выдумывать (твой же anti-hallucination принцип);
- `client_id` в ответе — строго из запроса;
- HTTP 4xx/5xx при ошибке с телом `{"error": "..."}`. Backend это переживает штатно: документ остаётся в статусе AwaitingAi, создаётся Failed-джоба, повторный запуск — `POST /api/documents/{id}/reprocess`;
- таймаут на стороне backend — 120 секунд, уложись;
- `GET /health` → 200 — для healthcheck в compose;
- детерминизм на демо-данных (temperature=0 или кэш) — демо должно быть воспроизводимым.

## 4. Read-API backend, доступный твоему сервису

Базовый URL внутри compose: `http://api:8080`. Swagger-документация: `http://localhost:8080/scalar/v1`.

| Метод | Путь | Что отдаёт |
|---|---|---|
| GET | `/api/documents` | список документов (метаданные, статусы) |
| GET | `/api/documents/{id}` | один документ |
| GET | `/api/documents/{id}/text` | полный нормализованный текст (последняя версия) |
| GET | `/api/documents/{id}/chunks` | чанки по порядку: `[{id, chunkIndex, content, tokenCount}]` |
| GET | `/api/regulatoryevents` | карточки изменений |
| GET | `/api/regulatoryevents/{id}/impacts` | затронутые клиенты с объяснениями |
| GET | `/api/clientprofiles` | профили клиентов (5 демо уже посеяны) |
| GET | `/api/notifications` | журнал уведомлений |

Аутентификации нет (MVP). Все enum'ы в JSON — строками.

## 5. Эмбеддинги и pgvector

PostgreSQL уже с расширением pgvector (образ `pgvector/pgvector:pg17`). Для твоего индекса:
- подключение: `Host=postgres;Port=5432;Database=regradar;Username=regradar;Password=<из .env>` (получишь env-переменной);
- создавай **свои** таблицы (например, `ai_embeddings (chunk_id uuid, embedding vector(N), metadata jsonb)`) — мои таблицы не изменяй, `chunk_id` бери из `/api/documents/{id}/chunks`;
- `CREATE EXTENSION IF NOT EXISTS vector;` выполнить при старте своего сервиса.

## 6. RAG-чат и генерация уведомлений

- **Чат** (`/chat` твоего сервиса): фронт будет ходить через backend-прокси (`/api/chat` → `http://ai:8000/chat`) — добавлю, когда у тебя будет endpoint. Контракт предложи сам (вопрос + режим юрист/клиент → ответ + источники: documentId + chunkId/фрагмент). History храни у себя или договоримся о таблице.
- **NotificationDraft**: сейчас backend сам собирает payload уведомления из карточки. Когда будет твой endpoint генерации клиентского текста — воткну его вызов перед отправкой в Bitrix (поле `full_message` поедет в payload). Не блокирует MVP.

## 7. Что нужно от тебя (чек-лист поставки)

1. Папка `ai/` в этот репозиторий: исходники + `Dockerfile` (порт 8000).
2. Endpoint `POST /analyze` по контракту §3 + `GET /health`.
3. Список env-переменных (ключ PolzaAI и т.п.) — добавлю в `.env.example`; ключи в коде не хранить.
4. 3–5 пар «вход → эталонный ответ» на seed-документах (лежат в `seed/*.txt`) — станут интеграционными тестами.
5. Промпты в `ai/prompts/` с версиями (backend пишет `promptVersion` в лог как есть).

## 8. Как проверить стыковку локально

1. `docker compose up -d --build` (после добавления твоего сервиса в compose — сделаю я).
2. `POST http://localhost:8080/api/ingestion/run` — загрузит seed-документы, пайплайн дернёт твой `/analyze`.
3. `GET /api/regulatoryevents` — карточки собраны из твоих ответов.
4. Таблица `LlmCallLogs` в БД — твой provider/model/latency в каждом вызове.
5. Пока твоего сервиса нет, backend работает на встроенном mock-провайдере — он же останется fallback'ом на демо (переключение конфигом, требование обоих наших ТЗ).
