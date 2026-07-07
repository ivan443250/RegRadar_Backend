# Данные AI-service, не попадающие во frontend, и расчёт scoring

## 1. Назначение документа

Документ описывает две связанные части текущей реализации RegRadar:

1. какие данные уже вычисляются внутри AI-service, но не входят в минимальный
   production-контракт `POST /analyze` и поэтому не могут быть показаны
   основным frontend без расширения API;
2. как детерминированно рассчитываются `impact_score`, `impact_level` и
   `relevance_score`.

Под «скором новости» далее понимается `impact_score` регуляторного документа.
Это оценка силы потенциального регуляторного влияния документа, а не вероятность
правильной классификации и не релевантность конкретному клиенту.

## 2. Какие данные получает backend сейчас

Минимальный production-контракт:

```text
POST /analyze
```

возвращает:

```text
provider
model
promptVersion
analysis
impact
clientRelevances
```

Этого достаточно, чтобы основной backend создал сокращённую карточку события,
показал общий impact и список затронутых клиентов. Однако внутренний pipeline
создаёт полный `RegulatoryEventCard`, notification drafts, типизированные
evidence и расширенную metadata. Эти части сокращаются при маппинге ответа
`/analyze`.

## 3. Что реализовано, но теряется для frontend

### 3.1. Document Analysis

Frontend получает через `/analyze`:

- `title`;
- `short_summary`, `long_summary`;
- `regulator`, `document_type`;
- `topics`, `affected_industries`;
- нормализованные `key_dates`;
- `obligations`;
- `source_fragments`;
- `confidence`.

Внутри `DocumentAnalysis` дополнительно существуют, но не возвращаются:

| Поле | Что мог бы показать frontend |
|---|---|
| `domain` | Нормализованный домен: `aml`, `personal_data`, `fuel_excise` и т.д. |
| `status` | Определённый статус документа |
| `affected_processes` | Какие процессы банка или клиента затронуты |
| `restrictions` | Ограничения, установленные документом |
| `penalties_or_consequences` | Ответственность, санкции и иные последствия |

Без этих полей интерфейс показывает итоговый impact, но не может разложить его
на обязанности, ограничения, процессы и последствия.

### 3.2. Impact Assessment

Frontend получает:

- `impact_score`;
- `impact_level`;
- `urgency`;
- `reasoning`;
- строковые `evidence_fragments`;
- `confidence`.

Внутри `ImpactAssessment` дополнительно существуют:

| Поле | Назначение |
|---|---|
| `bank_impact` | Человекочитаемое влияние на процессы банка |
| `client_impact` | Человекочитаемое влияние на бизнес клиента |
| `affected_processes` | До пяти затронутых процессов |
| `possible_consequences` | Последствия без выдумывания отсутствующих санкций |

Именно эти поля нужны для отдельных UI-блоков «Что проверить банку», «Что
изменится для клиента» и «Возможные последствия».

### 3.3. Client Relevance

Frontend получает ID клиента, score/level, matched factors, объяснения и
evidence. При сокращении теряются:

- `client_name` — backend может восстановить имя через `client_id`, но это
  требует join с профилями;
- `recommended_notification_type` — рекомендация `email` либо `push + email`.

### 3.4. Notification Drafts

AI-service уже создаёт для каждого релевантного клиента:

- `notification_id`;
- `client_id`, `client_name`;
- `title`;
- `short_message`, `full_message`;
- `client_friendly_explanation`;
- `source_link`;
- обязательный `disclaimer`;
- `priority`;
- `channel_payload`;
- `document_id`, `version_id`, `source_chunk_ids`.

В `/analyze` массив `notification_drafts` отсутствует полностью. Поэтому
основной frontend не может показать готовый текст клиентского уведомления,
priority, disclaimer и связь текста с источниками.

### 3.5. Event Card и review

Внутренний `RegulatoryEventCard` содержит:

- `event_id`;
- `current_status`;
- `review_state`;
- `review_required`;
- `created_by`;
- `source_set`;
- `no_data_reason`;
- полный Document Analysis, Impact, clients, notifications и metadata.

Минимальный контракт возвращает только отдельные части карточки. Frontend не
получает от AI явный признак `needs_review`, причину no-data и происхождение
карточки. Эти значения должен либо вернуть AI-service, либо единообразно
вычислить основной backend. Дублирование review-правил в двух сервисах создаст
риск расхождения.

### 3.6. Типизированные evidence

Полный `EvidenceFragment` содержит:

```text
fragment_id
text
source_type
document_id
version_id
chunk_id
source_url
evidence_role
```

В `/analyze` evidence представлены только строками. Кроме того, входной контракт
передаёт `chunks: string[]`, поэтому AI-service присваивает им локальные ID
`chunk_0`, `chunk_1` и не знает настоящие ID из PostgreSQL.

Из-за этого frontend может показать цитату, но не может надёжно реализовать
переход «открыть документ на конкретном фрагменте».

Для production evidence вход рекомендуется изменить на:

```json
{
  "chunks": [
    {
      "chunkId": "backend-chunk-guid",
      "chunkIndex": 0,
      "content": "Дословный фрагмент документа",
      "pageNumber": 3,
      "sectionTitle": "Статья 2"
    }
  ]
}
```

### 3.7. Analysis Metadata

Frontend сейчас получает только `provider`, `model`, `promptVersion`.

Полная `AnalysisMetadata` также содержит:

- runtime `POLZA`, `MOCK`, `FALLBACK` или `NO_DATA`;
- `fallback_used`, `fallback_reason`;
- `processing_mode`;
- `client_profiles_source`;
- `warnings`, включая language retry/fallback;
- `selected_model`;
- `request_id`, `llm_call_ids`, `latency_ms`;
- document/version context;
- результаты локального сохранения;
- `storage_source`.

Без этой metadata frontend не может объяснить, почему использован mock,
произошёл ли fallback, была ли исправлена языковая ошибка и с каким audit-call
связан результат.

### 3.8. RAG и Sources

`POST /api/rag/ask` уже возвращает:

- `answer`;
- `audience` (`bank_employee` или `client`);
- `no_data`;
- `safety_notice`;
- source fragments с `document_id/version_id/chunk_id/score`;
- полную AI metadata.

Этот endpoint не входит в минимальный production-контракт и пока не
проксируется основным backend. Поэтому основной frontend не получает чат по
документу, no-data режим и вкладку Sources.

### 3.9. Upload metadata

Standalone upload endpoints возвращают filename, content type, extracted text
length, chunks count и document/version IDs. В production загрузкой и
извлечением текста владеет основной backend, поэтому эти значения должен
показывать его собственный Documents API. Возвращать их повторно из
`/analyze` необязательно.

## 4. Как считается impact score документа

### 4.1. Источник данных для расчёта

Scoring выполняется после `DocumentAnalysis` и controlled domain normalization.
LLM не выставляет финальный score. `impact_engine.assess_impact()` получает:

- нормализованные topics/domain;
- obligations;
- penalties or consequences;
- key dates;
- affected processes;
- дословные source fragments.

Расчёт детерминирован: одинаковый `DocumentAnalysis` даёт одинаковый score.

### 4.2. Общие прибавки

Начальное значение — `0`.

| Условие | Изменение score |
|---|---:|
| Topic содержит «персональные данные» | `+30` |
| Topic содержит `115-ФЗ` или `ПОД/ФТ` | `+35` |
| Topic содержит `ВЭД` или «валютный контроль» | `+25` |
| Есть `penalties_or_consequences` | `+20` |
| Есть `obligations` | `+10` |
| Одновременно есть obligations и consequences | `+10` |
| Количество topics больше одного | `+10` |

Наличие consequences повышает score на `20` независимо от того, является ли
текст прямым штрафом или иной ответственностью. При этом reasoning различает
явные штрафы/санкции и общую ответственность.

### 4.3. Финансовый рынок и ценные бумаги

Если topics указывают на финансовый рынок или ценные бумаги:

| Условие | Изменение score |
|---|---:|
| Сам домен финансового рынка | `+25` |
| Организаторы торговли или котировальные списки | `+20` |
| Публичные акционерные общества | `+15` |
| Полномочия Банка России | `+15` |
| Есть значимая дата | `+10` |
| Есть поручения Правительству или Банку России | `+10` |

Если это только специализированное регулирование финансового рынка, нет других
сильных доменов и нет явных consequences, предварительный score ограничивается
значением `60`.

### 4.4. Топливо, нефтепереработка и акцизы

Для fuel/excise документов действуют дополнительные сигналы:

| Условие | Изменение score |
|---|---:|
| Упоминаются бензин или дизельное топливо | `+20` |
| Нефтяное сырьё или нефтепереработка | `+20` |
| Биржевые торги топливом | `+20` |
| Акцизы или налоговый период | `+20` |
| Изменение процента либо не менее двух key dates | `+10` |
| Document type — постановление | `+10` |

Если нет других сильных тем и consequences, итог специализированного
fuel/excise scoring также ограничивается `60`.

### 4.5. Доменные floor и cap

После суммирования тематических сигналов применяется правило detected domain.

`impact_floor` — минимальное значение для уверенно определённого домена.

`impact_cap` — верхняя граница, если в документе не обнаружены consequences.
При наличии реальных consequences cap домена не применяется.

| Domain | Floor | Cap без consequences |
|---|---:|---:|
| `personal_data` | 50 | 60 |
| `aml` | 61 | 80 |
| `product_marking_trade` | 40 | 60 |
| `lending_consumer_credit` | 40 | 60 |
| `fuel_excise` | 40 | 60 |
| `financial_market_securities` | 40 | 60 |
| `payments_digital_ruble` | 40 | 60 |
| `tax_reporting` | 40 | 60 |
| `foreign_trade_currency_control` | 40 | 60 |
| `info_security_it` | 40 | 60 |

Для `neutral_no_match` применяется отдельный cap `30`. Неизвестный или
нейтральный документ не может автоматически получить массовое высокое влияние.

### 4.6. Точный порядок операций

Порядок важен:

1. score начинается с `0`;
2. добавляются специализированные financial/fuel сигналы;
3. добавляются общие topic, obligation, consequence и complexity сигналы;
4. применяются specialized caps для financial/fuel без consequences;
5. применяется domain floor;
6. если consequences отсутствуют, применяется domain cap;
7. для `neutral_no_match` применяется cap `30`;
8. результат ограничивается диапазоном `0..100`;
9. score преобразуется в level и urgency.

Формально для распознанного домена:

```text
raw_score = сумма сработавших правил
score = max(raw_score, domain.impact_floor)

если consequences отсутствуют:
    score = min(score, domain.impact_cap)

score = clamp(score, 0, 100)
```

До этой формулы для financial/fuel может дополнительно сработать specialized
cap `60`.

### 4.7. Преобразование score в level

| Score | Impact level | Urgency |
|---:|---|---|
| `0–30` | `low` | `low` |
| `31–60` | `medium` | `medium` |
| `61–80` | `high` | `high` |
| `81–100` | `critical` | `critical` |

`confidence` deterministic impact engine сейчас фиксирован и равен `0.85`.
Это техническая уверенность baseline, а не статистически откалиброванная
вероятность.

### 4.8. Примеры

#### Персональные данные с обязанностями, но без consequences

```text
персональные данные                         +30
obligations                                 +10
domain personal_data floor                  до 50
domain cap без consequences                 максимум 60
итог                                        50, medium
```

#### Персональные данные с ответственностью

```text
персональные данные                         +30
obligations                                 +10
consequences                                +20
obligations + consequences                  +10
итог                                        70, high
```

Domain cap не применяется, потому что consequences реально присутствуют.

#### AML

```text
ПОД/ФТ                                      +35
несколько нормализованных topics            +10
domain aml floor                            минимум 61
domain cap без consequences                 максимум 80
```

Даже если сырой score ниже, уверенно определённый AML-домен получает минимум
`61`, то есть уровень `high`.

#### Топливное регулирование без санкций

Сигналы бензина, нефтепереработки, биржевых торгов и акцизов могут дать сырой
score выше `60`, однако без consequences специализированный и доменный caps
оставят результат на уровне `60`, то есть `medium`.

#### Neutral no-match

Даже если общие слова дали небольшой score, он ограничивается `30`. Клиенты и
notification drafts для no-match не создаются.

### 4.9. Reasoning, consequences и evidence

Каждое сработавшее правило добавляет человекочитаемую причину с весом, например:

```text
Тема затрагивает требования ПОД/ФТ и 115-ФЗ (+35)
Документ налагает обязательства (+10)
Одновременно установлены обязательства и последствия их нарушения (+10)
```

`reasoning` — объединение этих причин через `;`.

`possible_consequences` не должен придумывать штраф:

- если источник явно говорит о штрафе — это отражается как штраф;
- если указана только ответственность — используется нейтральная формулировка;
- если есть obligations, но последствия не названы — frontend должен показать,
  что последствия в источнике не уточнены;
- если данных нет — возвращается «Нет данных о санкциях в источнике».

Evidence собирается только из исходных `source_fragments`, obligations и
consequences, нормализуется для удаления дублей и ограничивается пятью
фрагментами. Если специальное evidence не найдено, используется первый исходный
source fragment.

## 5. Relevance score — отдельная оценка

`relevance_score` отвечает на другой вопрос: насколько уже отобранный документ
релевантен конкретному клиенту.

Клиент сначала проходит domain/topic gate. Нерелевантный клиент вообще не
получает score и не попадает в response.

Для прошедшего клиента:

```text
base score                                      50
совпадение domain client marker                +25
каждое профильное совпадение topic             +25
bonus от impact level:
    low                                          +0
    medium                                       +5
    high                                        +10
    critical                                    +15
maximum                                        100
```

Профильными совпадениями являются, например:

- personal data ↔ `handles_personal_data`, `personal_data`, `152-ФЗ`;
- AML ↔ medium/high cash operations, high risk, `115-ФЗ`, identification;
- ВЭД ↔ foreign trade/import/export;
- securities ↔ broker/issuer/investment/financial-market markers;
- fuel ↔ fuel/oil-processing/excise/exchange-trading markers.

Уровни client relevance:

| Relevance score | Level |
|---:|---|
| `0–40` | `low` |
| `41–70` | `medium` |
| `71–100` | `high` |

После scoring дополнительно требуется непустой `matched_factors`. Это защищает
от формального попадания клиента без объяснимого пересечения профиля и темы.

## 6. Что рекомендуется добавить в production API

Чтобы основной frontend отображал уже реализованный функционал, достаточно
расширить response `/analyze` следующими optional-блоками:

```json
{
  "metadata": {
    "fallbackUsed": false,
    "fallbackReason": null,
    "warnings": [],
    "requestId": "...",
    "llmCallIds": [],
    "latencyMs": 1200
  },
  "review": {
    "state": "needs_review",
    "required": true,
    "noDataReason": null
  },
  "evidence": [],
  "notificationDrafts": []
}
```

Также необходимо передавать реальные chunk IDs во входном запросе. RAG/chat
лучше оставить отдельным контрактом `POST /api/chat` или backend proxy к
`POST /api/rag/ask`, а не включать его в синхронный анализ документа.

## 7. Источники реализации

- `app/ai/impact_engine.py` — impact score, level, reasoning и evidence;
- `app/ai/domain_rules.py` — domain detection, floor/cap и client markers;
- `app/ai/service.py` — client relevance score и notification drafts;
- `app/ai/schemas.py` — полные внутренние response models;
- `app/integrations/main_backend/backend_contract.py` — сокращение данных для
  production `/analyze`.
