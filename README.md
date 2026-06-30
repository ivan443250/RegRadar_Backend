# RegRadar Backend

Backend-контур платформы регуляторной разведки RegRadar: ingestion документов,
обработка, хранение, REST API, интеграции с AI-модулем и Bitrix.

## Стек

- ASP.NET Core (.NET 10), C#
- PostgreSQL + pgvector
- Redis
- EF Core (миграции), Docker Compose
- OpenAPI (встроенный) + Scalar UI

## Структура решения

| Проект | Назначение |
|---|---|
| `RegRadar.Domain` | сущности, enum'ы, доменные интерфейсы |
| `RegRadar.Application` | сервисы, DTO, контракты, валидация |
| `RegRadar.Infrastructure` | EF Core, репозитории, адаптеры |
| `RegRadar.Workers` | фоновые джобы (ingestion, processing) |
| `RegRadar.Api` | REST API, host, OpenAPI |
| `RegRadar.Tests` | xUnit-тесты |

## Запуск через Docker

```bash
cp .env.example .env   # заполнить значения
docker compose up --build
