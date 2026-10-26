// Все обращения фронта к API — только здесь. Контракт: docs/api/openapi.json (Swagger: /api/docs).
import { clearSession, readSession, request, saveSession } from './http.js';

export { ApiError, fieldErrors } from './http.js';

// ---------- Авторизация ----------

// Пользователь текущей вкладки: { accountId, role, name, inn? } или null
export const currentSession = () => readSession()?.user ?? null;

export const getTestAccounts = () => request('GET', '/auth/test-accounts');

export async function login(accountId) {
  const res = await request('POST', '/auth/login', { body: { accountId } });
  saveSession({ accessToken: res.accessToken, user: res.user, expiresAt: Date.now() + res.expiresIn * 1000 });
  return res.user;
}

export async function logout() {
  try { await request('POST', '/auth/logout'); } catch { /* токен мог уже истечь — выходим всё равно */ }
  clearSession();
}

// { user, company, currentApplicationId }
export const getMe = () => request('GET', '/me');
export const getMyCompany = () => request('GET', '/me/company');

// ---------- Каталог и справочники ----------

export const getProducts = () => request('GET', '/products');
export const recommend = (input) => request('POST', '/assistant/recommend', { body: input });

// Справочники не меняются за сессию — запрашиваем один раз на вкладку.
// При ошибке кеш сбрасывается, чтобы следующий экран запросил их заново.
let dictionaries;
export function getDictionaries() {
  dictionaries ??= request('GET', '/dictionaries').catch((err) => {
    dictionaries = undefined;
    throw err;
  });
  return dictionaries;
}

// ---------- Заявки клиента ----------

export const listMyApplications = () => request('GET', '/applications');
export const getApplication = (id) => request('GET', `/applications/${id}`);

// Черновик: создаётся сразу, сохраняется по шагам, отправляется с согласиями
export const createDraft = (data) => request('POST', '/applications', { body: data });
export const updateDraft = (id, data) => request('PATCH', `/applications/${id}`, { body: data });
export const submitApplication = (id, consents, idempotencyKey) =>
  request('POST', `/applications/${id}/submit`, { body: { consents }, headers: { 'Idempotency-Key': idempotencyKey } });

// Ответ на запрос дополнительной информации: answers = [{code, value}]
export const respondInfo = (id, answers, comment) =>
  request('POST', `/applications/${id}/info`, { body: { answers, comment: comment || null } });

export const acceptOffer = (id) => request('POST', `/applications/${id}/offer/accept`);
export const declineOffer = (id) => request('POST', `/applications/${id}/offer/decline`);

// { sentAt, expiresAt, attemptsLeft, code? } — code приходит только в демо-режиме (DEMO_SHOW_SIGN_CODE)
export const requestSignCode = (id) => request('POST', `/applications/${id}/sign/code`);
export const signContract = (id, code) => request('POST', `/applications/${id}/sign`, { body: { code } });

// ---------- Аналитик ----------

export const listApplications = (status) =>
  request('GET', `/analyst/applications${status ? `?status=${encodeURIComponent(status)}` : ''}`);
export const getAnalystApplication = (id) => request('GET', `/analyst/applications/${id}`);
// Повторный запрос ЕГРЮЛ/ЕГРИП, НБКИ и «Прозрачного бизнеса»; статус не меняется, ответ — обновлённая карточка
export const refreshChecks = (id) => request('POST', `/analyst/applications/${id}/checks/refresh`);
// { action, amount?, commentForClient?, reasonCode?, infoItems? }
export const decide = (id, body) => request('POST', `/analyst/applications/${id}/decision`, { body });

// ---------- Демо ----------

export const resetDemo = () => request('POST', '/demo/reset');
