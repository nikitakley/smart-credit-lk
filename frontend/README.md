# Фронтенд — кабинет клиента и аналитика

React 19 + Vite, без TypeScript и UI-библиотек. Данные — только из API бэкенда (`/api`).

## Запуск

1. Поднимите бэкенд на :8000 — см. корневой README (`uv run uvicorn app.main:app --reload` или `docker compose up --build`).
2. В папке `frontend`:

```bash
npm install
npm run dev
```

Откройте http://localhost:5173. Vite проксирует `/api` на `http://localhost:8000`; другой адрес — через переменную `API_TARGET`:

```bash
API_TARGET=http://localhost:8080 npm run dev
```

Сборка: `npm run build`, просмотр сборки: `npm run preview` (прокси тот же).

## Демо-входы

На экране входа — тестовые учётные записи из `GET /api/auth/test-accounts`:

| Учётная запись | Что показать |
|---|---|
| prodmarket | Контрпредложение A-1024 → принять → подписать → выдача; черновик A-1020 |
| vektor | Одобрение A-1022 → подписание; A-1026 в обработке |
| sidorov | Запрос информации A-1023 → ответ клиента |
| sibtorg | A-1025 на проверке у специалиста |
| uralstroy | Отказ A-1021 с объяснением |
| analyst | Очередь заявок и решение по A-1025 |

Кнопка «Сбросить демо-данные» в очереди аналитика вызывает `POST /api/demo/reset`.

## Устройство

- `src/api/http.js` — запросы, токен в `sessionStorage` (своя сессия на вкладку), ошибки `{error:{code,message,fields}}` → `ApiError`; при 401 — на `/login`.
- `src/api/client.js` — все эндпоинты. Справочники запрашиваются один раз; если `GET /api/dictionaries` недоступен, берётся локальная копия `DICTIONARIES_FALLBACK`.
- `src/api/useLoad.js` — загрузка с перезапросом после любых изменений и опросом (`pollMs`) на страницах статуса и очереди.
- `src/config/statuses.js` — подписи статусов и шаги таймлайна.
- `src/styles/tokens.css` — дизайн-токены.
