// HTTP-слой: JWT из сессии, единый разбор ошибок бэкенда {error: {code, message, fields}}.
// Базовый путь относительный (/api) — в dev его проксирует Vite (vite.config.js).
const API_BASE = '/api';
const SESSION_KEY = 'smart-credit-session';
export const CHANGE_EVENT = 'smart-credit-change';

export class ApiError extends Error {
  constructor(status, code, message, fields = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.fields = fields; // [{field, code, message}]
  }
}

// Сессия в sessionStorage — своя у каждой вкладки: клиент и аналитик работают рядом
export function readSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY)); } catch { return null; }
}

export function saveSession(session) {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(session)); } catch { /* без хранилища вход не переживёт перезагрузку */ }
}

export function clearSession() {
  try { sessionStorage.removeItem(SESSION_KEY); } catch { /* нечего чистить */ }
}

// Сообщить экранам, что данные изменились (useLoad перезапросит)
export const notifyChange = () => window.dispatchEvent(new Event(CHANGE_EVENT));

export async function request(method, path, { body, headers } = {}) {
  const session = readSession();
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'network_error', 'Сервер недоступен. Проверьте, что бэкенд запущен.');
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null);

  if (!res.ok) {
    // Токен истёк или недействителен — выходим на страницу входа
    if (res.status === 401 && session) {
      clearSession();
      window.location.assign('/login');
    }
    const e = data?.error;
    throw new ApiError(res.status, e?.code ?? 'http_error', e?.message ?? `Ошибка сервера (${res.status})`, e?.fields ?? []);
  }

  if (method !== 'GET') notifyChange();
  return data;
}

// Ошибки полей с сервера → { amount: 'Сумма должна быть…', 'consents.bki': '…' }
export function fieldErrors(error) {
  return Object.fromEntries((error?.fields ?? []).map((f) => [f.field, f.message]));
}
