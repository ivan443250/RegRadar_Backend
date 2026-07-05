# RegRadar Backend

Backend-контур платформы регуляторной разведки RegRadar: ingestion документов из источников,
обработка (извлечение текста, дедупликация, чанкинг), AI-анализ (mock), карточки регуляторных
изменений, оценка влияния на клиентов банка и уведомления (Bitrix/mock).

## Стек

- ASP.NET Core (.NET 10), C#
- PostgreSQL + pgvector, EF Core (миграции)
- Redis
- Фоновый воркер (BackgroundService) для ingestion
- Docker Compose, OpenAPI (встроенный) + Scalar UI

## Структура решения

| Проект | Назначение |
|---|---|
| `RegRadar.Domain` | сущности, enum'ы |
| `RegRadar.Application` | порты (интерфейсы), DTO, контракты |
| `RegRadar.Infrastructure` | EF Core, пайплайн обработки, ингесторы, impact-движок, адаптеры AI/Bitrix |
| `RegRadar.Workers` | фоновый воркер периодического ingestion |
| `RegRadar.Api` | REST API |
| `RegRadar.Tests` | xUnit-тесты ключевых сервисов |

## Запуск через Docker

```bash
cp .env.example .env   # заполнить значения
docker compose up --build
```

Поднимаются: api (:8080), фоновый worker, PostgreSQL (pgvector), Redis.

Применить миграции (первый запуск):

```bash
dotnet tool restore
dotnet ef database update --project src/RegRadar.Infrastructure --startup-project src/RegRadar.Api
```

- API: http://localhost:8080
- Документация (Scalar): http://localhost:8080/scalar/v1
- OpenAPI JSON: http://localhost:8080/openapi/v1.json
- Health: http://localhost:8080/health · Readiness: http://localhost:8080/health/ready

## Сквозной сценарий (demo)

1. `POST /api/ingestion/run` — забрать документы из источников (RSS Банка России + seed-файлы из `seed/`); дедупликация по SHA-256 делает запуск идемпотентным.
2. Или загрузить свой файл: `POST /api/documents/upload` (PDF/DOCX/TXT).
3. Документ проходит пайплайн: extract → normalize → hash → chunks → mock-AI → карточка `RegulatoryEvent` → расчёт затронутых клиентов.
4. `GET /api/regulatoryevents` — карточки изменений; `GET /api/regulatoryevents/{id}/impacts` — затронутые клиенты с объяснением.
5. `POST /api/notifications/send` `{ "regulatoryEventId": "...", "clientProfileId": "..." }` — уведомление в Bitrix (реальный webhook через `BITRIX_WEBHOOK_URL` в `.env`) или mock-режим, если URL не задан.
6. Трассировка для аудита: `ProcessingJobs`, `LlmCallLogs`, `AuditLogs` в БД; `POST /api/documents/{id}/reprocess` — повторный запуск AI-шага.

Демо-клиенты (5 профилей: интернет-магазин, импортёр, ресторанная сеть, IT/SaaS, наличная розница)
создаются автоматически при старте API.

## Основные эндпойнты

| Метод | Путь | Что делает |
|---|---|---|
| POST | `/api/documents/upload` | загрузка файла (multipart) |
| POST | `/api/documents/{id}/reprocess` | повторный AI-анализ документа |
| GET | `/api/documents` | список документов со статусами |
| POST | `/api/ingestion/run` | ручной запуск всех ингесторов |
| GET | `/api/regulatoryevents` | карточки регуляторных изменений |
| GET | `/api/regulatoryevents/{id}/impacts` | затронутые клиенты |
| POST | `/api/regulatoryevents/{id}/impacts/recalculate` | пересчёт влияния |
| GET/POST | `/api/clientprofiles` | профили клиентов |
| GET | `/api/notifications` | журнал уведомлений |
| POST | `/api/notifications/send` | отправка уведомления (Bitrix/mock) |
| GET/POST | `/api/sources` | источники |

## Локальный запуск (без Docker)

Нужны PostgreSQL и Redis (строки подключения в `appsettings.Development.json`).

```bash
dotnet run --project src/RegRadar.Api       # API
dotnet run --project src/RegRadar.Workers   # фоновый ingestion
```

## Тесты

```bash
dotnet test
```

## Конфигурация

Все секреты — через переменные окружения / `.env` (не коммитятся, шаблон — `.env.example`).
Ключевые настройки: `Chunking` (размер/перекрытие чанков), `Storage` (путь хранения оригиналов),
`Ingestion` (интервал воркера), `BankOfRussia` (URL RSS), `Notifications__BitrixWebhookUrl`.

## Архитектурные заметки

- Пайплайн обработки един для всех каналов (upload / RSS / seed) — `IDocumentProcessingService`.
- AI-модуль за портом `IAiAnalysisService`: сейчас детерминированный mock (fallback для демо),
  реальный провайдер подключается заменой одной DI-регистрации.
- Impact-движок — объяснимые правила (`RuleBasedImpactAssessor`): каждый вывод сопровождается
  списком затронутых факторов.
- Дедупликация: SHA-256 нормализованного текста + уникальные индексы БД.
- pgvector заложен в образ БД; эмбеддинги чанков — следующий шаг (RAG-ассистент AI-модуля).
