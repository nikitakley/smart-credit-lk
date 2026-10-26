# Описание API

| Что | Где |
|---|---|
| Спецификация OpenAPI 3.1 — API кабинета | [`openapi.json`](openapi.json) · Swagger UI: http://localhost:8000/api/docs |
| Спецификация OpenAPI — симулятор внешних источников | [`mocks-openapi.json`](mocks-openapi.json) · Swagger UI: http://localhost:8001/docs |
| Коллекция запросов (Postman v2.1, импортируется в Bruno и Insomnia) | [`../collection/smart-credit-lk.postman_collection.json`](../collection/smart-credit-lk.postman_collection.json) |

Обе спецификации генерируются из кода (`scripts/export_openapi.py`) и проверяются тестами на актуальность.

## Общие правила

- **Базовый адрес** — `http://localhost:8000/api`. Во фронтенде запросы идут на тот же адрес `/api` (прокси).
- **Формат** — JSON, поля в camelCase. Суммы — целые рубли, даты — ISO 8601 в UTC.
- **Вход** — без регистрации: клиент уже обслуживается в банке. `POST /auth/login` с `accountId` тестовой учётки →
  `accessToken` (JWT, 8 часов) → заголовок `Authorization: Bearer <accessToken>`. Выход — клиент удаляет токен.
- **Роли**: `client` — сотрудник компании-клиента, видит только заявки своей компании; `analyst` — специалист банка,
  видит все заявки, кроме черновиков.
- **Две проекции заявки**: клиент получает `ApplicationClient` — без оценки, рекомендации системы, разбивки ставки,
  баллов факторов и данных источников; специалист — `ApplicationAnalyst` со всеми полями.
- **Идемпотентная подача**: `POST /applications/{id}/submit` с заголовком `Idempotency-Key` — повтор запроса
  (например, при обрыве связи) возвращает тот же результат, а не второй раз подаёт заявку.

## Эндпоинты

### Служебное, вход, справочники

| Метод и путь | Кто | Назначение |
|---|---|---|
| `GET /health` | все | состояние сервиса и базы: 200 `ok` / 503 `degraded` |
| `POST /demo/reset` | все, демо-режим | вернуть демо-данные в исходное состояние |
| `GET /auth/test-accounts` | все, демо-режим | тестовые учётные записи для экрана входа |
| `POST /auth/login` | все | вход по тестовой учётке |
| `POST /auth/logout` | вошедший | выход |
| `GET /me` | вошедший | пользователь; у клиента — компания и текущая заявка |
| `GET /me/company` | клиент | реквизиты своей компании (известны банку, не вводятся) |
| `GET /products` | все | каталог кредитных продуктов |
| `POST /assistant/recommend` | все | подбор продукта по цели, сумме, сроку и залогу (правила, без ИИ) |
| `GET /dictionaries` | все | цели, залоги, причины отказа, типовые запросы информации, причины недоступности источников |

### Заявка клиента

| Метод и путь | Статус заявки | Результат |
|---|---|---|
| `GET /applications` | — | список своих заявок |
| `POST /applications` | — | черновик (`draft`); поля можно заполнять постепенно |
| `GET /applications/{id}` | любой | заявка: статус, история, проверки, решение, оффер, договор |
| `PATCH /applications/{id}` | `draft` | сохранить изменённые поля |
| `POST /applications/{id}/submit` | `draft` | подать с согласиями на запрос в БКИ и обработку данных → `submitted` |
| `POST /applications/{id}/info` | `docs_requested` | ответ на запрос информации → `validation` |
| `POST /applications/{id}/offer/accept` | `approved`, `counter_offer` | принять предложение → `signing`, формируется договор |
| `POST /applications/{id}/offer/decline` | `approved`, `counter_offer` | отказаться → `declined_by_client` |
| `POST /applications/{id}/sign/code` | `signing` | код подписи: 6 цифр, 5 минут, 3 попытки; в демо-режиме возвращается в ответе |
| `POST /applications/{id}/sign` | `signing` | подписать кодом → `issued`, деньги зачислены на расчётный счёт (моделируется) |

### Специалист банка

| Метод и путь | Статус заявки | Результат |
|---|---|---|
| `GET /analyst/applications?status=` | — | очередь, новые сверху, фильтр по статусу |
| `GET /analyst/applications/{id}` | любой, кроме `draft` | полная карточка: оценка, факторы, данные источников, рекомендация системы |
| `POST /analyst/applications/{id}/decision` | `manual_review`, `docs_requested` | `approve`, `counter_offer` (сумма меньше запрошенной), `request_docs` (что запросить), `reject` (причина из справочника); комментарий клиенту обязателен, кроме `approve` |
| `POST /analyst/applications/{id}/checks/refresh` | `enrichment`, `scoring`, `manual_review`, `docs_requested` | заново запросить ЕГРЮЛ/ЕГРИП, НБКИ и «Прозрачный бизнес»; статус не меняется, в историю пишется событие |

## Проверки и данные источников

Проверка (`checks[]`): `source` (`bank`, `egrul`, `nbki`, `pb`), `status` (`ok`, `warning`, `fail`, `unavailable`),
`summary` — текст для человека. Специалист дополнительно видит `details` — данные источника по схеме,
зависящей от `source` (`BankDetails`, `RegistryDetails`, `CreditHistoryDetails`, `RiskDetails`),
а при `status = unavailable` — `UnavailableDetails` с причиной: `timeout`, `connection_error`, `server_error`,
`request_rejected`, `invalid_response` (подписи — в `GET /dictionaries`).

## Ошибки

Любая ошибка — в одном формате:

```json
{"error": {"code": "validation_error", "message": "Проверьте введённые данные",
           "fields": [{"field": "consents.bki", "code": "required", "message": "Нужно согласие на запрос в БКИ"}]}}
```

`message` — готовый текст для пользователя; `fields` — ошибки по полям (имена в camelCase).

| HTTP | Коды | Что делать клиенту API |
|---|---|---|
| 401 | `unauthorized` | войти заново |
| 403 | `forbidden` | действие недоступно роли |
| 404 | `application_not_found`, `company_not_found`, `account_not_found`, `not_found` | объект не найден или чужой |
| 409 | см. ниже | показать `message` и перечитать заявку: её состояние изменилось |
| 422 | `validation_error` (с `fields`), `invalid_code` | исправить ввод |
| 500 | `internal_error` | повторить позже |

Коды 409 — по каждому эндпоинту перечислены в Swagger; полный список — `CONFLICT_CODES` в `backend/app/errors.py`:

| Код | Значение |
|---|---|
| `not_draft` | заявка уже не черновик |
| `invalid_transition` | действие недопустимо в текущем статусе заявки |
| `concurrent_update` | заявку одновременно изменил другой запрос |
| `no_offer`, `offer_expired` | нет действующего предложения / срок предложения истёк |
| `not_signing` | договор сейчас не на подписании |
| `code_not_requested`, `code_expired`, `code_attempts_exceeded` | код подписи не запрашивался / истёк / попытки закончились |
| `no_info_request` | банк не запрашивал дополнительную информацию |
| `decision_not_allowed` | решение по заявке в этом статусе не принимается |
| `checks_refresh_not_allowed` | в этом статусе данные из источников не запрашиваются |
| `not_submitted` | заявка ещё не подана |

## Симулятор внешних источников

Отдельный сервис (`http://localhost:8001`), заменяет внешние системы. Доступ — заголовок `X-Api-Key`.

| Метод и путь | Источник |
|---|---|
| `GET /egr/v1/extracts/{inn}` | ЕГРЮЛ (10-значный ИНН) / ЕГРИП (12-значный) |
| `POST /nbki/v1/credit-reports` | НБКИ: кредитный отчёт, только с действующим согласием субъекта |
| `GET /pb/v1/companies/{inn}` | ФНС «Прозрачный бизнес»: признаки риска |
| `GET /admin/sources`, `PUT /admin/sources/{source}`, `POST /admin/reset` | управление задержками и сбоями источников |
| `GET /admin/requests` | журнал последних запросов банка с `X-Request-Id` |

Подробно — [`mocks/README.md`](../../mocks/README.md).
