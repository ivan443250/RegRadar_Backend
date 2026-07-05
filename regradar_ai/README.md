# RegRadar AI-service

RegRadar AI-service — отдельный FastAPI-сервис для AI-анализа регуляторных
документов. Основной `.NET RegRadar.Api` вызывает его по HTTP внутри Docker
Compose; AI-service не пишет напрямую в основную PostgreSQL-базу.

Подробности:

- [production integration](docs/MAIN_BACKEND_INTEGRATION.md);
- [внутренний facade](docs/AI_SERVICE_INTEGRATION.md);
- [AI pipeline](docs/AI_MODULE_PIPELINE.md);
- [данные для frontend и scoring](docs/FRONTEND_DATA_GAPS_AND_SCORING.md);
- [curl/Docker demo](docs/DEMO_SCRIPT.md).

## Production contract

```text
GET  /health
POST /analyze
```

В общей Docker network основной backend обращается к:

```text
http://ai:8000/health
http://ai:8000/analyze
```

### POST /analyze

Пример request:

```json
{
  "documentId": "document-guid",
  "title": "Изменения требований",
  "text": "Полный нормализованный текст документа",
  "chunks": ["Готовый чанк 0", "Готовый чанк 1"],
  "clients": [
    {
      "clientId": "client-guid",
      "companyName": "ООО ИмпортТрейд",
      "okved": "46.69",
      "industry": "Оптовая торговля, ВЭД",
      "size": "Medium",
      "hasForeignTrade": true,
      "usesOnlinePayments": false,
      "handlesPersonalData": false,
      "cashOperationsLevel": "Medium",
      "riskProfile": "High",
      "bankSegment": "SME"
    }
  ]
}
```

Response содержит только согласованный контракт:

```json
{
  "provider": "polza",
  "model": "deepseek/deepseek-v4-flash",
  "promptVersion": "document_analysis_v1",
  "analysis": {},
  "impact": {},
  "clientRelevances": []
}
```

Гарантии:

- переданные `clientId` сохраняются без подмены;
- `clients=[]` возвращает `clientRelevances=[]` без demo seed fallback;
- готовые chunks используются в переданном порядке;
- даты возвращаются как grounded `{date, meaning}` либо `null`;
- endpoint не запускает RAG/chat/notification mock-send;
- ошибки имеют форму `{"error":"понятное описание"}`;
- deadline по умолчанию — 120 секунд;
- LLM Gateway использует `temperature=0.0`.

Примеры:

- [минимальный request без клиентов](docs/examples/analyze_minimal_request.json);
- [request с клиентами](docs/examples/analyze_with_clients_request.json);
- [полный backend contract](docs/examples/backend_contract_analyze_request.json).

## Responsibilities

AI-service отвечает за:

- `DocumentAnalysis`;
- `ImpactAssessment` controlled baseline;
- `ClientRelevance` controlled matching;
- source-grounded fragments;
- provider/model/promptVersion metadata;
- PolzaAI/mock/fallback и language guard;
- внутренний LLM audit.

Основной backend отвечает за:

- ingestion и нормализацию документов;
- PostgreSQL, chunks, statuses/jobs;
- `RegulatoryEvents`, `ClientImpacts`, `Notifications`;
- основной `LLMCallLogs` audit;
- review, authorization и delivery workflow.

## Run locally

```powershell
cd regradar_ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env
```

Проверка:

```powershell
curl.exe http://127.0.0.1:8000/health

curl.exe -X POST http://127.0.0.1:8000/analyze `
  -H "Content-Type: application/json" `
  --data-binary "@docs/examples/analyze_with_clients_request.json"
```

Swagger: `http://127.0.0.1:8000/docs`.

## Run with Docker

```powershell
docker build -t regradar-ai:local .
docker network create regradar-network

docker run --rm -d `
  --name ai `
  --network regradar-network `
  -p 8000:8000 `
  --env-file .env `
  regradar-ai:local
```

Проверка с host:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Проверка внутри Docker network:

```powershell
docker run --rm --network regradar-network `
  curlimages/curl:8.10.1 http://ai:8000/health
```

Логи и остановка:

```powershell
docker logs -f ai
docker stop ai
```

`.env` исключён из Git и Docker build context. `POLZA_API_KEY` передаётся только
контейнеру `ai`.

## Environment

| Переменная | Default | Назначение |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock`, `polza`, `polza_with_fallback` |
| `POLZA_API_KEY` | — | Секрет PolzaAI; только AI-service |
| `POLZA_BASE_URL` | `https://polza.ai/api/v1` | OpenAI-compatible base URL |
| `POLZA_MODEL` | config default | Default model ID |
| `POLZA_ALLOWED_MODELS` | allowlist | Разрешённые model IDs |
| `POLZA_TIMEOUT_SECONDS` | `60` | Provider HTTP timeout |
| `POLZA_MAX_RETRIES` | `2` | Provider retry count |
| `BACKEND_CONTRACT_TIMEOUT_SECONDS` | `120` | Deadline `/analyze` |
| `MAIN_BACKEND_URL` | — | Optional read API, в compose `http://api:8080` |
| `MAIN_BACKEND_TIMEOUT_SECONDS` | `30` | Read API timeout |
| `REG_RADAR_STORAGE_DIR` | `data/storage` | Writable JSONL runtime directory |
| `REG_RADAR_LOG_DIR` | `data/logs` | Writable LLM audit directory |

Никакие API-ключи не хранятся в коде, examples или документации.

## Debug and standalone capabilities

Production backend должен использовать только `/health` и `/analyze`.
Для разработки и диагностики сохранены:

- `/api/integration/main-backend/*` — расширенный integration payload/read API;
- `/api/ai/full-analysis`, `/api/ai/document-analysis`, `/api/ai/models`;
- upload TXT/PDF и EventCard endpoints;
- `/api/rag/ask` — keyword RAG-lite;
- `/api/notifications/mock-send`;
- `/api/debug/*` — локальные audit/persistence views.

Они не являются обязательной частью production-контракта `.NET` backend.

## Tests

```powershell
python -m pytest
python -m scripts.run_real_samples_eval
```

Тесты не выполняют реальные внешние HTTP/LLM-вызовы. Real-doc evaluation
использует `data/real_samples` и проверяет 39 enabled документов.

## Project layout

```text
app/                                 FastAPI и AI-service
app/ai/prompts/                      versioned prompts
app/integrations/main_backend/       production/extended contracts
app/storage/                         replaceable JSONL runtime boundary
tests/                               backend and integration tests
scripts/                             evaluation/diagnostic scripts
data/real_samples/                   real-document evaluation dataset
docs/examples/                       переносимые JSON requests
Dockerfile                           container ai:8000
.dockerignore                        secrets/runtime exclusions
```

Текущие ограничения: JSONL — локальная persistence-lite, RAG использует keyword
retrieval, OCR и production delivery adapters отсутствуют. Pgvector-backed RAG
и `/chat` требуют отдельного согласованного контракта.
