# Документация RegRadar

Эта папка хранит исходные материалы проекта и контрактные заметки. Актуальный главный вход в проект — [корневой README](../README.md).

## Основные документы

| Документ | Назначение |
|---|---|
| [API-для-AI-модуля.md](API-для-AI-модуля.md) | Исторический и контрактный документ по стыковке основного backend и AI-модуля |
| [ТЗ.md](ТЗ.md) | Исходное техническое задание на backend/ingestion/data platform |
| [RegRadar.pdf](RegRadar.pdf) | Презентационный материал проекта |
| [RegRadar Overview.pdf](RegRadar%20Overview.pdf) | Краткий overview проекта |
| [screenshots/](screenshots/) | Рекомендуемая папка для скриншотов интерфейса, которые вставляются в README |

## Актуальная техническая документация AI-service

AI-service расположен в [`../regradar_ai`](../regradar_ai/).

| Документ | Назначение |
|---|---|
| [AI-service README](../regradar_ai/README.md) | Запуск, production-контракт `/health` и `/analyze`, env, тесты |
| [AI pipeline](../regradar_ai/docs/AI_MODULE_PIPELINE.md) | Полный AI pipeline и API surface |
| [AI service integration](../regradar_ai/docs/AI_SERVICE_INTEGRATION.md) | Facade, операции, metadata, degraded mode |
| [Main backend integration](../regradar_ai/docs/MAIN_BACKEND_INTEGRATION.md) | Production и extended contracts для основного backend |
| [Demo script](../regradar_ai/docs/DEMO_SCRIPT.md) | Curl/Docker demo-сценарий |
| [Frontend data gaps and scoring](../regradar_ai/docs/FRONTEND_DATA_GAPS_AND_SCORING.md) | Что AI-service считает, что видит frontend, и как считается scoring |
| [Real docs evaluation](../regradar_ai/docs/evaluation/REAL_DOCS_EVAL.md) | Набор реальных документов и expected outcomes |

## Быстрые команды

Из корня репозитория:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Проверки:

```powershell
dotnet test

cd regradar_ai
python -m pytest -q
python -m scripts.run_real_samples_eval
```

