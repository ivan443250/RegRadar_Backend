# RegRadar AI-service Demo Script

Демо проводится напрямую через production HTTP contract.

## 1. Подготовка

- локальный `.env` не коммитится;
- для PolzaAI ключ задаётся только в environment AI-service;
- без ключа используется `LLM_PROVIDER=mock` или safe fallback;
- Docker service name в общей network — `ai`.

## 2. Запуск контейнера

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

## 3. Healthcheck

```powershell
curl.exe http://127.0.0.1:8000/health
```

Показать:

- `status`;
- `service=regradar-ai`;
- `providerMode`, `defaultModel`;
- prompts и storage statuses.

Healthcheck не вызывает LLM.

## 4. Анализ без клиентов

```powershell
curl.exe -X POST http://127.0.0.1:8000/analyze `
  -H "Content-Type: application/json" `
  --data-binary "@docs/examples/analyze_minimal_request.json"
```

Проверить:

- HTTP 200;
- `provider`, `model`, `promptVersion`;
- заполнены `analysis` и `impact`;
- `clientRelevances=[]`;
- demo seed profiles не использовались;
- source fragments основаны на request chunks.

## 5. Анализ с клиентами

```powershell
curl.exe -X POST http://127.0.0.1:8000/analyze `
  -H "Content-Type: application/json" `
  --data-binary "@docs/examples/analyze_with_clients_request.json"
```

Проверить:

- `client_id` совпадает с request `clientId`;
- relevance имеет score, level, factors и объяснения;
- даты представлены `{date, meaning}` или `null`;
- response не содержит EventCard, notifications, RAG/chat history.

Короткое объяснение:

> LLM извлекает DocumentAnalysis. Impact и client matching остаются controlled
> baseline. AI-service возвращает structured result, а основной backend владеет
> PostgreSQL, jobs, RegulatoryEvents, ClientImpacts и Notifications.

## 6. Проверка ошибки

Отправить request с пустым `text`. Ожидается HTTP 400:

```json
{"error":"text must not be empty"}
```

Stacktrace и полный document text наружу не возвращаются.

## 7. Совместное демо с main backend

В общем compose основной backend использует:

```text
GET  http://ai:8000/health
POST http://ai:8000/analyze
```

Далее:

1. вызвать `POST http://localhost:8080/api/ingestion/run`;
2. проверить `GET http://localhost:8080/api/regulatoryevents`;
3. проверить backend `LLMCallLogs`;
4. убедиться, что provider/model/promptVersion сохранены.

## 8. Debug capabilities

При отдельной диагностике доступны `/api/ai/health`, `/api/rag/ask`,
`/api/debug/*` и расширенные `/api/integration/main-backend/*`. Они не входят в
минимальный production contract.

## 9. Проверки перед передачей

```powershell
python -m pytest
python -m scripts.run_real_samples_eval
docker build -t regradar-ai:local .
```

Также проверить `/health` и `/analyze` в собранном container.

## 10. 30-second pitch

> RegRadar AI-service принимает нормализованный регуляторный документ, готовые
> chunks и клиентские профили. Через LLM Gateway он извлекает структурированный
> DocumentAnalysis, controlled baseline рассчитывает impact и релевантность
> клиентов, а основной .NET backend сохраняет результат и управляет дальнейшим
> workflow. Сервис имеет mock/fallback, grounded sources, audit и стабильный
> Docker HTTP contract.
