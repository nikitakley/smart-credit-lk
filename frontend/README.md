# Фронтенд — кабинет клиента и аналитика

React 19 + Vite, без TypeScript и UI-библиотек. Данные — только из API бэкенда (`/api`).

## Запуск

1. Поднимите бэкенд из корня репозитория — API на :8000, подробности в `backend/README.md`:

```bash
docker compose up --build -d
```

2. В папке `frontend`:

```bash
npm ci
npm run dev
```

Откройте http://localhost:5173. Vite проксирует `/api` на `http://localhost:8000`; другой адрес — через переменную `API_TARGET`:

```bash
API_TARGET=http://localhost:8080 npm run dev
```

Сборка: `npm run build`, просмотр сборки: `npm run preview` (прокси тот же).

## Docker

`Dockerfile` собирает фронтенд (`npm ci && npm run build` в `node:24-alpine`) и раздаёт `dist/` через `nginx:1.28-alpine`.
`nginx.conf`: любой маршрут отдаёт `index.html` (роутинг на клиенте), `/api/` проксируется на `http://api:8000` —
сервис `api` из `docker-compose.yml`.

```bash
docker build -t smart-credit-frontend ./frontend
```

В `docker-compose.yml` фронтенд — сервис `frontend`: `docker compose up --build -d` из корня, затем http://localhost:8080
(порт меняется переменной `WEB_PORT`). Сервис стартует после того, как `api` станет healthy.

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

- `src/api/http.js` — запросы, токен в `sessionStorage` (своя сессия на вкладку), ошибки `{error:{code,message,fields}}` → `ApiError`; при 401 — на `/login`, при 409 — перечитывание данных, 5xx и обрыв сети — «Сервис временно недоступен».
- `src/api/client.js` — все эндпоинты. Справочники запрашиваются один раз на вкладку.
- `src/api/useLoad.js` — загрузка с перезапросом после любых изменений; `useApplication` опрашивает заявку с интервалом по статусу (`applicationPollMs` в `src/config/statuses.js`).
- `src/components/ChecksList.jsx` — проверки банка; у аналитика — блок «Подробнее» с `details`.
- `src/config/statuses.js` — подписи статусов, шаги таймлайна и интервалы опроса.
- `src/styles/tokens.css` — дизайн-токены.
