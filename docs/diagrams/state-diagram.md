# Диаграмма состояний заявки

Статусы и разрешённые переходы — таблица `TRANSITIONS` в `backend/app/services/state_machine.py`.
Любой переход вне таблицы — ошибка `409 invalid_transition`; каждый переход записывается в историю заявки.

```mermaid
stateDiagram-v2
    direction LR
    [*] --> draft: клиент создаёт черновик
    draft --> submitted: клиент подаёт (согласия)

    submitted --> validation: система*
    validation --> enrichment: система*
    validation --> docs_requested: система*
    validation --> rejected: система*

    enrichment --> scoring: система*
    enrichment --> rejected: стоп-фактор*
    enrichment --> manual_review: источник недоступен*

    scoring --> approved: система*
    scoring --> counter_offer: система*
    scoring --> rejected: система*
    scoring --> manual_review: «серая зона»*
    scoring --> docs_requested: мало данных*

    manual_review --> approved: специалист
    manual_review --> counter_offer: специалист
    manual_review --> rejected: специалист
    manual_review --> docs_requested: специалист

    docs_requested --> validation: клиент ответил
    docs_requested --> approved: специалист
    docs_requested --> counter_offer: специалист
    docs_requested --> rejected: специалист

    approved --> signing: клиент принял
    counter_offer --> signing: клиент принял
    approved --> declined_by_client: клиент отказался
    counter_offer --> declined_by_client: клиент отказался
    signing --> issued: подписание кодом → выдача

    rejected --> [*]
    issued --> [*]
    declined_by_client --> [*]
```

`*` — переходы выполняет конвейер обработки (этап 4, в разработке). Сейчас поданная заявка остаётся в `submitted`;
заявки во всех статусах обработки и решения есть в демо-данных, и с ними работают специалист и клиент.

| Статус | Подпись в интерфейсе | Кто действует |
|---|---|---|
| `draft` | Черновик | клиент заполняет заявку |
| `submitted` | Заявка подана | — |
| `validation` | Проверяем заявку | конвейер (этап 4) |
| `enrichment` | Запрашиваем данные в БКИ и ФНС | конвейер (этап 4); специалист может обновить данные |
| `scoring` | Оцениваем заявку | конвейер (этап 4) |
| `manual_review` | Рассматривает специалист | специалист принимает решение |
| `docs_requested` | Нужна дополнительная информация | клиент отвечает или специалист решает |
| `approved` | Одобрено | клиент принимает или отказывается |
| `counter_offer` | Контрпредложение | клиент принимает или отказывается |
| `signing` | Подписание договора | клиент подписывает кодом |
| `issued` | Кредит выдан | конечный |
| `rejected` | Отказ | конечный |
| `declined_by_client` | Клиент отказался | конечный |

Кроме смены статуса история заявки содержит события без смены статуса (`kind = checks_refreshed` — данные
из источников запрошены повторно). Они пишутся функцией `record_event()` и таблицу переходов не обходят.

Полноту графа проверяют тесты `backend/tests/test_state_machine.py`: каждый статус достижим из черновика,
из каждого незавершённого статуса есть путь к конечному, история каждой демо-заявки — допустимый путь.
