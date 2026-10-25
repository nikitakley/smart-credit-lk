# Фронтенд кредитного кабинета — саммари для бэкенда

Состояние на 25.10.2026, первый перенос фронтенда в общий репозиторий. Описано только то, что есть в коде `frontend/`.

Главное: **фронт пока не ходит в сеть.** Все данные идут через один модуль `src/api/client.js`, который сейчас читает и пишет демо-хранилище в `localStorage`. Функции в нём асинхронные и названы по будущим эндпоинтам (путь указан комментарием над каждой). Чтобы подключить бэк, нужно заменить тела этих функций на HTTP-запросы. Экраны трогать не придётся.

---

## 1. Стек и версии

Источник — `frontend/package.json`.

| Что | Чем | Версия |
| --- | --- | --- |
| UI | React, React DOM | ^19.3.1 |
| Сборка и dev-сервер | Vite + `@vitejs/plugin-react` | ^8.3.4 / ^6.1.2 |
| Роутинг | `react-router-dom` (`BrowserRouter`) | ^7.18.4 |
| UI-библиотека | **нет** — свои компоненты в `src/components`, стили в `src/styles/tokens.css` и `app.css` | — |
| Шрифт | `@fontsource-variable/manrope`, подключён локально | ^5.3.0 |
| HTTP-клиент | **нет** (ни `fetch`, ни axios в коде нет) | — |
| Управление состоянием | **нет библиотеки**: `useState` в страницах + свой хук `useLoad` (`src/api/useLoad.js`) | — |
| Язык | JavaScript (JSX), без TypeScript | — |
| Тесты, линтер | **нет** | — |

`useLoad(load, deps)` вызывает асинхронную функцию API и возвращает `{ data, error, loading }`. Данные перезапрашиваются при событии `alfa-demo-change`, то есть при любой записи в демо-хранилище, в том числе из соседней вкладки. С настоящим бэком это событие само не придёт: понадобится поллинг или WebSocket (см. п. 10).

## 2. Запуск локально

Нужен Node.js (проверено на 24.x) и npm.

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

```bash
npm run build      # сборка в frontend/dist
npm run preview    # просмотр сборки
```

Переменных окружения, `.env`-файлов и прокси на бэкенд в `vite.config.js` нет. Dockerfile тоже нет.

Сбросить демо-данные можно кнопкой «Сбросить демо-данные» в очереди аналитика или очисткой `localStorage` в браузере.

## 3. Маршруты

Источник — `src/App.jsx`. Клиентские маршруты закрыты `ClientLayout`, аналитические — `AnalystLayout`: без входа под нужной ролью идёт редирект на `/login`.

| Путь | Роль | Экран | Состояние |
| --- | --- | --- | --- |
| `/` | — | Редирект на `/assistant` | Готово |
| `/login` | — | Вход по тестовым учёткам | Готово (демо-вход без пароля) |
| `/assistant` | клиент | Помощник подбора: анкета из 4 вопросов → продукты | Готово, подбор по правилам |
| `/catalog` | клиент | Каталог продуктов | Готово, каталог статичный |
| `/apply` | клиент | Мастер заявки, 4 шага | Готово |
| `/applications/:id` | клиент | Статус заявки, таймлайн, решение или выдача | Готово |
| `/applications/:id/decision` | клиент | «Почему такое решение»: факторы и объяснение | Готово |
| `/applications/:id/offer` | клиент | Предложение банка: принять или отказаться | Готово |
| `/applications/:id/sign` | клиент | Подписание договора кодом и выдача | Готово, подписание смоделировано |
| `/analyst` | аналитик | Очередь заявок | Готово, фильтры на клиенте |
| `/analyst/applications/:id` | аналитик | Карточка заявки и решение | Готово |
| `*` | — | 404 | Готово |

Заглушки на экранах:
- на `/applications/:id` при статусе `docs_requested` написано «Загрузка документов — после согласования с бэком», самой загрузки нет;
- компонент `Placeholder` в коде остался, но экраны его больше не используют.

## 4. Экраны

Типы ниже — как в демо-данных. Суммы — целые рубли, даты — ISO 8601 со смещением.

### `/login` — вход

- **Показывает:** список тестовых учёток из `getTestAccounts()`. Поля: `id`, `role` (`client` | `analyst`), `inn` (у клиента), `name`, `hint`.
- **Ввод:** нет.
- **Действия:** клик по учётке вызывает `login(accountId)`. Клиент попадает на `/assistant`, аналитик — на `/analyst`.

### `/assistant` — помощник подбора

- **Ввод:** 4 вопроса, ответ кнопкой, все обязательные (без ответа дальше не пройти).

  | Ключ | Значения |
  | --- | --- |
  | `purpose` | `working_capital`, `cash_gap`, `equipment`, `renovation` |
  | `amount` | `400000`, `2000000`, `6000000`, `15000000` (диапазоны «до 500 тыс.», «0,5–3 млн», «3–10 млн», «больше 10 млн») |
  | `termMonths` | `12`, `24`, `48` |
  | `collateral` | `real_estate`, `equipment`, `none` |

- **Действия:** после 4-го ответа вызывается `recommend({purpose, amount, termMonths, collateral})`. Ответ — `{ summary, items: [{ product, best, reasons[], caveat }] }`. Правила лежат в `src/api/assistantMock.js`: порядок продуктов зависит от цели, продукты, чьи лимиты не подходят под сумму или срок, отсеиваются.
- **«Оформить»** у продукта открывает `/apply?product=<id>&amount=<amount>&term=<termMonths>&purpose=<purpose>`. «Пройти заново» сбрасывает анкету.

### `/catalog` — каталог

- **Показывает:** `getProducts()` — `id`, `name`, `note`, `minAmount`, `maxAmount`, `maxTermMonths`, `rateFrom` (`spread` в данных есть, но на экран не выводится). Пример — в п. 5.
- **Действия:** «Оформить» → `/apply?product=<id>`.

### `/apply` — мастер заявки

Query-параметры: `product` (по умолчанию `working-capital`), `amount` (`2000000`), `term` (`24`), `purpose` (`working_capital`). Срок, превышающий `maxTermMonths` продукта, автоматически прижимается к максимуму.

1. **«Компания».** При открытии вызывается `getCompany(inn из сессии)`, поля только для чтения:
   - `inn`, `name`;
   - `ogrn` (у ИП подпись «ОГРНИП»);
   - `kpp` (у ИП `null`, поле скрыто);
   - `registeredAt`, `director`, `okved {code, title}`, `legalAddress`;
   - источник `source` и дата `fetchedAt`.

   Кнопка «Всё верно, дальше». При ошибке показывается «Не удалось получить данные из ЕГРЮЛ — попробуйте позже».
2. **«Контакты».** Предзаполнены из профиля (`director`, `phone`, `email`), можно править.

   | Поле | Обяз. | Проверка на фронте |
   | --- | --- | --- |
   | `contact.name` | да | не пусто |
   | `contact.phone` | да | `/^\+?[\d\s()-]{10,}$/` |
   | `contact.email` | да | `/^\S+@\S+\.\S+$/` |

3. **«Условия».**

   | Поле | Обяз. | Проверка |
   | --- | --- | --- |
   | `productId` | да | один из трёх продуктов |
   | `amount` | да | только цифры; `minAmount ≤ amount ≤ maxAmount` продукта |
   | `termMonths` | да | выбор из `3, 6, 12, 18, 24, 36, 48, 60`, но не больше `maxTermMonths` |
   | `purpose` | да | `working_capital`, `cash_gap`, `equipment`, `renovation`, `refinancing` |

   Ниже показывается расчёт «от»: `rateFrom` продукта и аннуитетный платёж.
4. **«Отправка».** Сводка и два чекбокса, оба обязательны: «Согласие на запрос в БКИ» и «Согласие на обработку персональных данных».
   - Красная кнопка «Отправить заявку» вызывает `createApplication({productId, amount, termMonths, purpose, contact})` и переходит на `/applications/<id>`.
   - Согласия в API **не передаются**, проверяются только на фронте.

### `/applications/:id` — статус заявки

- **Показывает:** `getApplication(id)`:
  - номер, компания, продукт, запрошенные `amount` и `termMonths`;
  - бейдж статуса;
  - кольцо «пройдено этапов» и таймлайн из `history[]` (см. п. 8).
- **Правая карточка по состоянию:**
  - есть `issuance` → «Кредит выдан»: сумма, номер договора, `signedAt`, счёт `•••• XXXX`;
  - статус `signing` → «Осталось подписать договор» и кнопка на `/applications/:id/sign`;
  - есть `decision` → заголовок решения, кнопки «Почему такое решение» и «Предложение банка» (если есть `offer`);
  - `docs_requested` → `note` последней записи истории;
  - иначе — «Появится после проверки».

### `/applications/:id/decision` — почему такое решение

- **Показывает:**
  - `decision.outcome` (бейдж);
  - заголовок вида «Одобрено 1 500 000 ₽ вместо 2 000 000 ₽», строится из `decision.approvedAmount` и `decision.requestedAmount`;
  - `decision.commentForClient`;
  - `factors[]` (`label`, `detail`, `impact`, `weight`);
  - `aiExplanation.text` с подписью «Объяснение простыми словами»;
  - `improvements[]`.
- **Не показывает клиенту:** `score`.
- **Действия:** «Посмотреть предложение» (если есть `offer`) и «К статусу заявки».

### `/applications/:id/offer` — предложение

- **Показывает:**
  - `offer.amount`, `termMonths`, `rate`, `monthlyPayment`, `validUntil`;
  - разбивку ставки `offer.rateBreakdown`;
  - для `counter_offer` — таблицу «в заявке / предложение» по `offer.requested`.
- **Действия:**
  - «Принять предложение» → `acceptOffer(id)`, переход на `/sign`. Кнопка неактивна, если `validUntil` в прошлом.
  - «Отказаться» → `declineOffer(id)`, переход на статус.
  - «Почему такие условия» → `/decision`.
  - Если клиент уже ответил (`signing` / `issued` / `declined_by_client`), вместо кнопок показываются бейдж и ссылка.

### `/applications/:id/sign` — подписание и выдача

- **Показывает:** `signing.contractNumber`, заёмщик, продукт, сумма, срок, ставка, платёж, счёт зачисления.
- **Ввод:** чекбокс «Ознакомился с условиями договора», обязательный, и код подтверждения — ровно 6 цифр.
- **Действия:**
  - «Получить код для подписи» → `requestSignCode(id)`. Ответ `{code, sentAt}`. **Код показывается прямо на экране** с пометкой «Демо».
  - «Новый код» запрашивает код повторно.
  - «Подписать и получить деньги» → `signContract(id, code)`. Ошибка `invalid_code` выводит «Код не подходит…». Успех переводит на статус, уже с выдачей.
- Если статус не `signing`, экран показывает только сообщение и ссылку на статус.

### `/analyst` — очередь

- **Показывает:** `listApplications()`, сортировка по `createdAt` по убыванию. В строке: аватар, `company.name`, `id`, `company.inn`, `amount`, `createdAt`, бейдж статуса.
- **Цифры в hero считаются на фронте:** всего заявок, «ждут решения» (`submitted` / `scoring`), «нужны документы», доля решений с `decision.followedAi = true`.
- **Ввод:** фильтр-чипсы «Все / Ждут решения / Нужны документы / С решением» — фильтрация на клиенте.
- **Действия:** клик по строке → карточка. «Сбросить демо-данные» пересоздаёт демо-хранилище (только для демо).

### `/analyst/applications/:id` — карточка заявки

- **Показывает:**
  - реквизиты компании;
  - `score` (`value`, `max`, `minScore`) кольцом и текстом;
  - `scoringInputs`: выручка, динамика, платежи по кредитам и их доля, просрочки, срок работы, «можно выдать до»;
  - `rateBreakdown`, `factors[]`, `history[]` с `actor` и `note`;
  - `aiRecommendation.text` с подписью «Рекомендация системы».
- **Ввод:** «Сумма контрпредложения, ₽» (по умолчанию `aiRecommendation.amount`, при рекомендации отказа пусто) и «Комментарий для клиента».
- **Проверки:**
  - для контрпредложения сумма должна быть больше 0 и меньше запрошенной;
  - комментарий обязателен для всех действий, кроме «Одобрить».
- **Действия** (доступны при статусе `submitted`, `scoring`, `docs_requested`) — все вызывают `decide(id, {...})`:
  - «Одобрить <запрошенная сумма>» — `action: 'approve'`, `amount = app.amount`;
  - «Контрпредложение» — `action: 'counter_offer'`, `amount` из поля;
  - «Запросить документы» — `action: 'request_docs'`;
  - «Отказать» — `action: 'reject'`, `reasonCode: 'debt_load'` (**захардкожен**).

  `termMonths` и `rate` всегда берутся из `aiRecommendation`, аналитик их **не меняет**.
- **После решения** показываются бейдж, заголовок, комментарий и «Совпадает / Отличается от рекомендации системы».

## 5. Моковые данные

| Файл | Что внутри |
| --- | --- |
| `src/api/store.js` | Сид и хранилище: `COMPANIES` (5 компаний, одна ликвидирована), `PRODUCTS` (3), `TEST_ACCOUNTS` (4), `makeApplication`, `applyDecision`, `startSigning`, `issueSignCode`, `completeSigning`, `seed()` |
| `src/api/scoring.js` | Правила скоринга, объяснения, список улучшений |
| `src/api/assistantMock.js` | Правила помощника подбора |

**Хранение:** `localStorage['alfa-cabinet-demo-v3']` — объект `{ nextNumber, currentByInn: { [inn]: applicationId }, applications: { [id]: Application } }`. Все данные синтетические.

**Сид:**

| Заявка | Компания | Статус |
| --- | --- | --- |
| A-1024 | ООО «Ромашка» | `scoring` |
| A-1023 | ИП Сидоров | `docs_requested` |
| A-1022 | ООО «Вектор» | `approved` |
| A-1021 | ООО «Альтаир» | `rejected` |

**Компания** (`COMPANIES['7701000001']`):

```json
{
  "inn": "7701000001", "type": "legal", "status": "active",
  "name": "ООО «Ромашка»", "ogrn": "1027700000001", "kpp": "770101001",
  "registeredAt": "2024-06-12", "director": "Иванов Иван Иванович",
  "okved": { "code": "47.19", "title": "Розничная торговля" },
  "legalAddress": "г. Москва, ул. Примерная, д. 1, оф. 10",
  "phone": "+7 900 000-00-01", "email": "finance@romashka.example",
  "account": "40702810000000000421",
  "source": "ФНС", "fetchedAt": "2026-10-20T10:12:00+03:00",
  "finance": { "monthlyRevenue": 1600000, "revenueGrowth": 18, "loanPayments": 720000, "overdues24m": 0 }
}
```

`type`: `legal` | `ip`. У ИП `kpp: null`. `status`: `active` | `liquidated`. `finance` — синтетическая «выписка» за 12 месяцев, вход для скоринга.

**Продукт.** `rateFrom` = ключевая ставка 14 + `spread`:

```json
{ "id": "working-capital", "name": "Оборотный кредит", "note": "Пополнение оборотных средств",
  "minAmount": 300000, "maxAmount": 10000000, "maxTermMonths": 36, "spread": 4.5, "rateFrom": 18.5 }
```

Остальные продукты: `investment` («Кредит на развитие», 1–30 млн, до 60 мес., 17,9%) и `overdraft` («Овердрафт», 0,1–5 млн, до 12 мес., 19,5%).

**Тестовая учётка:**

```json
{ "id": "romashka", "role": "client", "inn": "7701000001", "hint": "Заявка на проверке — пройдите сделку до выдачи" }
```

Остальные учётки: `vector`, `sidorov` (клиенты) и `analyst`.

**Заявка** — A-1024 после решения «контрпредложение», подписания и выдачи; служебные поля сокращены:

```json
{
  "id": "A-1024",
  "company": { "...": "объект компании целиком, как выше" },
  "productId": "working-capital", "productName": "Оборотный кредит",
  "amount": 2000000, "termMonths": 24, "purpose": "working_capital",
  "contact": { "name": "Иванов Иван Иванович", "phone": "+7 900 000-00-01", "email": "finance@romashka.example" },
  "status": "issued",
  "createdAt": "2026-10-20T10:12:00+03:00",
  "history": [
    { "status": "submitted", "at": "2026-10-20T10:12:00+03:00", "actor": "client" },
    { "status": "scoring", "at": "2026-10-20T10:13:00+03:00", "actor": "system", "note": "Проверяем выписку и данные ФНС" },
    { "status": "counter_offer", "at": "…", "actor": "analyst", "note": "Снизили сумму из-за долговой нагрузки" },
    { "status": "signing", "at": "…", "actor": "client", "note": "Предложение принято, сформирован договор КД-1024/2026" },
    { "status": "issued", "at": "…", "actor": "system", "note": "Договор подписан, деньги зачислены на счёт •••• 0421" }
  ],
  "score": { "value": 680, "max": 1000, "minScore": 450 },
  "factors": [
    { "code": "revenue_trend", "label": "Растущая выручка", "detail": "Выручка за 12 месяцев выросла на 18%", "impact": "positive", "weight": "high", "points": 120 },
    { "code": "debt_load", "label": "Высокая долговая нагрузка", "detail": "Платежи по текущим кредитам — 45% выручки (лимит 50%)", "impact": "negative", "weight": "medium", "points": -80 },
    { "code": "credit_history", "label": "Нет просрочек", "detail": "Кредитная история без просрочек за 2 года", "impact": "positive", "weight": "medium", "points": 80 },
    { "code": "business_age", "label": "Срок работы бизнеса", "detail": "2 года 4 месяца", "impact": "neutral", "weight": "low", "points": 0 }
  ],
  "scoringInputs": { "monthlyRevenue": 1600000, "revenueGrowth": 18, "loanPayments": 720000, "overdues24m": 0,
                     "ageMonths": 28, "dtiNow": 45, "dtiWithRequested": 51, "affordable": 1500000 },
  "rateBreakdown": { "keyRate": 14, "productSpread": 4.5, "riskPremium": 1, "rate": 19.5 },
  "aiRecommendation": { "outcome": "counter_offer", "amount": 1500000, "termMonths": 24, "rate": 19.5,
                        "text": "Контрпредложение: 1 500 000 ₽ вместо 2 000 000 ₽. С запрошенной суммой платежи по кредитам заняли бы 51% выручки при лимите 50%." },
  "decision": { "outcome": "counter_offer", "requestedAmount": 2000000, "approvedAmount": 1500000,
                "decidedBy": "analyst", "decidedAt": "…", "commentForClient": "Снизили сумму из-за долговой нагрузки",
                "followedAi": true },
  "aiExplanation": { "text": "Сумму снизили до 1 500 000 ₽: с 2 000 000 ₽ платежи по всем кредитам заняли бы 51% выручки при лимите 50%. …",
                     "generatedAt": "…", "source": "rules" },
  "improvements": ["Погасить часть текущих кредитов: лимит нагрузки — 50% выручки", "Добавить залог или поручительство", "Перевести обороты на счёт в Альфа-Банке — банк увидит выручку точнее"],
  "offer": { "type": "counter_offer", "amount": 1500000, "termMonths": 24, "rate": 19.5,
             "rateBreakdown": { "keyRate": 14, "productSpread": 4.5, "riskPremium": 1, "rate": 19.5 },
             "monthlyPayment": 76000, "collateralRequired": "none", "validUntil": "…(+7 дней от решения)",
             "requested": { "amount": 2000000, "termMonths": 24, "collateral": "none" } },
  "signing": { "contractNumber": "КД-1024/2026", "createdAt": "…", "code": null, "codeSentAt": "…", "signedAt": "…" },
  "issuance": { "contractNumber": "КД-1024/2026", "signedAt": "…", "issuedAt": "…", "amount": 1500000, "account": "40702810000000000421" }
}
```

Пояснения к полям:
- **До решения** `decision`, `offer`, `aiExplanation`, `signing`, `issuance` равны `null`, `improvements` — `[]`.
- **`aiRecommendation` и `aiExplanation` строятся правилами** (`scoring.js`), а не моделью. Поля названы так по контракту.
- **`weight`** выводится из `|points|`: от 100 — `high`, от 50 — `medium`, меньше — `low`.
- **`collateral` в заявке не хранится:** в оффере он всегда `none`.

**Правила скоринга** — `src/api/scoring.js`, сводка:
- **Оценка** = 560 + баллы четырёх факторов, от 0 до 1000; порог одобрения 450.
- **Ставка** = 14 + `spread` + надбавка за риск: 0 при оценке от 700, 1 — от 550, 2,5 — ниже.
- **Сумма:** платежи по всем кредитам вместе с новым — не больше 50% выручки (обратный аннуитет, округление вниз до 100 000 ₽).
- **Исход:** `rejected`, если оценка ниже 450 или допустимая сумма меньше `minAmount`; `approved`, если запрошенное укладывается в лимит; иначе `counter_offer` на максимум в пределах лимита.

## 6. Взаимодействие с сервером

- **HTTP-запросов в коде нет.** `fetch` и axios не используются, базовый адрес API и переменные окружения не заданы.
- **Все обращения к данным** — только через `src/api/client.js`. Над каждой функцией комментарием указан планируемый эндпоинт:

| Функция | Планируемый эндпоинт | Вход → выход |
| --- | --- | --- |
| `getTestAccounts()` | `GET /api/auth/test-accounts` | → `[{id, role, inn?, name, hint}]` |
| `login(accountId)` | `POST /api/auth/login` | → `{role, accountId, inn?, name}` |
| `logout()` | `POST /api/auth/logout` | → — |
| `getClientSession()` | (эндпоинта нет — собирается на фронте) | → `{...session, company, applicationId}` |
| `getCompany(inn)` | `GET /api/companies/{inn}` | → компания; ошибки `invalid_inn`, `company_not_found`, `company_inactive` |
| `getProducts()` | `GET /api/products` | → `[product]` |
| `recommend(input)` | `POST /api/assistant/recommend` | `{purpose, amount, termMonths, collateral}` → `{summary, items[]}` |
| `createApplication(data)` | `POST /api/applications` | `{productId, amount, termMonths, purpose, contact}` → `{id}`; ИНН берётся из сессии; без сессии клиента — `unauthorized` |
| `getApplication(id)` | `GET /api/applications/{id}` | → заявка целиком; `application_not_found` |
| `acceptOffer(id)` | `POST /api/applications/{id}/offer/accept` | → заявка в `signing`; `no_offer` |
| `declineOffer(id)` | `POST /api/applications/{id}/offer/decline` | → заявка в `declined_by_client` |
| `requestSignCode(id)` | `POST /api/applications/{id}/sign/code` | → `{code, sentAt}` (демо); `not_signing` |
| `signContract(id, code)` | `POST /api/applications/{id}/sign` | → заявка в `issued`; `invalid_code`, `not_signing` |
| `listApplications()` | `GET /api/analyst/applications` | → `[application]` |
| `decide(id, input)` | `POST /api/analyst/applications/{id}/decision` | `{action, amount, termMonths, rate, commentForClient, reasonCode?}` → заявка |
| `resetDemo()` | — (только демо) | — |

- **Ошибки:** `client.js` бросает `ApiError` с полем `code`. Экраны сейчас обрабатывают коды только у `getCompany` (мастер) и `signContract` (подписание). Формат ошибок валидации 422 из контракта (`{errors:[{field, code}]}`) фронт **пока не разбирает**.
- **Обновление данных:** экраны перечитывают данные только по событию изменения хранилища. Поллинга и WebSocket нет.

## 7. Авторизация

- **Есть демо-вход** по 4 тестовым учёткам, без пароля:
  - клиенты `romashka`, `vector`, `sidorov` — действующие клиенты банка, регистрации нет;
  - `analyst`.
- **Роли:** `client` и `analyst`. Кабинеты защищены проверкой роли в `ClientLayout` и `AnalystLayout`, без нужной роли — редирект на `/login`.
- **Хранение сессии:** `sessionStorage['alfa-cabinet-session']` — JSON `{role, accountId, inn?, name}`, своя сессия у каждой вкладки. **Токена нет**, заголовок `Authorization` не отправляется (запросов нет).
- **Выход:** меню аватара → «Выйти» → `logout()` → `/login`.
- **Привязка к компании:** заявка создаётся от ИНН из сессии. «Моя заявка» в шапке берёт `currentByInn[inn]` — последнюю созданную заявку компании.

## 8. Статусы заявки

Источник — `src/config/statuses.js`.

| Код | Подпись в интерфейсе | Тон бейджа |
| --- | --- | --- |
| `submitted` | Заявка подана | info |
| `scoring` | Проверяем данные | info |
| `docs_requested` | Нужны документы | warning |
| `approved` | Одобрено | success |
| `counter_offer` | Контрпредложение | warning |
| `rejected` | Отказ | error |
| `signing` | Подписание договора | info |
| `issued` | Кредит выдан | success |
| `declined_by_client` | Клиент отказался | info |

- **Основной путь для таймлайна:** `submitted → scoring → approved → signing → issued`. `docs_requested` занимает место `scoring`, `counter_offer` — место `approved`.
- **Терминальные статусы:** `rejected`, `issued`, `declined_by_client`.
- **Кто ставит статус** (`actor` в истории): `client`, `system`, `analyst`. На экране подписи «клиент», «система», «аналитик».

## 9. Что не реализовано или ждёт сервера

- **Сеть:** HTTP-слоя, базового URL, переменных окружения и обработки сетевых ошибок нет.
- **Авторизация:** нет токена и реального входа — Альфа-ID, ДБО или пароли.
- **Документы:** после `docs_requested` загрузить их нельзя; вернуть заявку в `scoring` из интерфейса тоже нельзя.
- **Аналитик:** не может менять срок и ставку в решении; `reasonCode` при отказе всегда `debt_load`.
- **Согласия** из мастера не уходят в API.
- **Скоринг, рекомендации, объяснения и подбор** считаются на фронте, в моках. На бэке их нужно повторить или заменить. LLM в коде нет.
- **Код подписи** в демо возвращается в ответе и показывается на экране. На проде он должен уходить в SMS или push и проверяться только на бэке.
- **Списки:** пагинации, серверной фильтрации и сортировки очереди нет — всё на клиенте.
- **Каталог продуктов и 5 компаний** зашиты в `store.js`. Поиск компании по ИНН работает только по ним.
- **Повторная заявка** после отказа создаётся как новая, связи со старой нет.
- **Инфраструктура:** нет Dockerfile, README по запуску, тестов и линтера.

## 10. Открытые вопросы к бэкенду

1. **Базовый адрес API и конфиг.** Фронту нужна переменная вроде `VITE_API_URL` (её пока нет) или прокси в `vite.config.js`. Какой вариант и какой порт?
2. **Авторизация.** Какой токен (JWT, cookie-сессия), где хранить, как передавать? Отдаёт ли `GET /api/auth/test-accounts` список учёток?
3. **Где живёт скоринг.** Бэк переносит правила из `src/api/scoring.js` как есть? Должна ли рекомендация считаться при создании заявки, как сейчас?
4. **Формат заявки.** Устраивает ли структура из п. 5 (заявка целиком с `company`, `factors`, `offer`, `signing`, `issuance`)? Или клиенту отдаём урезанную версию без `score`, `scoringInputs`, `aiRecommendation`?
5. **Подписание.** Возвращать ли код в ответе `sign/code` в демо-режиме, или выводить его иначе, например в лог? Сколько живёт код и сколько даётся попыток?
6. **Ошибки.** Единый формат тела ошибки и HTTP-коды для `invalid_code`, `no_offer`, `not_signing`, `unauthorized` и ошибок валидации 422.
7. **Обновление статуса** у клиента: поллинг (с каким интервалом) или WebSocket?
8. **Документы** при `docs_requested`: делаем загрузку (эндпоинт, форматы, лимиты) или оставляем только статус?
9. **Решение аналитика:** нужны ли изменяемые срок и ставка и справочник `reasonCode`?
10. **Согласия:** передавать ли `consents {bki, personalData}` в `POST /api/applications`?
11. **Очередь:** нужны ли серверные фильтры, сортировка и пагинация в `GET /api/analyst/applications`?
12. **CORS и время:** даты в ISO 8601 со смещением `+03:00`, как в демо, — подходит?
