# Сборка фронтенда: node собирает dist/, nginx раздаёт статику и проксирует /api на бэкенд.
# Проверка: docker build -t smart-credit-frontend ./frontend

FROM node:24-alpine AS build
WORKDIR /app
# Сначала только манифесты — слой с зависимостями кешируется, пока не меняется lock-файл
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
