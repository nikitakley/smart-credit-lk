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

// ВРЕМЕННО: копия справочников из backend/app/api/routes/catalog.py. GET /api/dictionaries
// сейчас отвечает 500 (в роуте поле purposes, в схеме purpose). Убрать после исправления на бэке.
const DICTIONARIES_FALLBACK = {
  purposes: [
    { code: 'working_capital', label: 'Пополнение оборотных средств' },
    { code: 'cash_gap', label: 'Кассовый разрыв' },
    { code: 'equipment', label: 'Покупка оборудования' },
    { code: 'renovation', label: 'Ремонт и развитие' },
    { code: 'refinancing', label: 'Рефинансирование' },
  ],
  collateralTypes: [
    { code: 'real_estate', label: 'Недвижимость' },
    { code: 'equipment', label: 'Оборудование' },
    { code: 'none', label: 'Без залога' },
  ],
  rejectReasons: [
    { code: 'debt_load', label: 'Высокая долговая нагрузка' },
    { code: 'credit_history', label: 'Негативная кредитная история' },
    { code: 'company_inactive', label: 'Компания не действует' },
    { code: 'insufficient_data', label: 'Недостаточно данных для оценки' },
    { code: 'risk_signals', label: 'Признаки повышенного риска' },
    { code: 'other', label: 'Другая причина' },
  ],
  infoItems: [
    { code: 'monthly_revenue_confirm', label: 'Среднемесячная выручка за 6 месяцев, ₽', type: 'number', required: true },
    { code: 'main_bank', label: 'Банк, где ведутся основные обороты', type: 'text', required: true },
    { code: 'purpose_details', label: 'Подробнее о цели кредита', type: 'text', required: true },
    { code: 'actual_address', label: 'Фактический адрес ведения бизнеса', type: 'text', required: true },
  ],
};

// Справочники не меняются за сессию — запрашиваем один раз на вкладку
let dictionaries;
export function getDictionaries() {
  dictionaries ??= request('GET', '/dictionaries')
    .then((d) => ({ ...d, purposes: d.purposes ?? d.purpose }))
    .catch((err) => {
      console.warn('GET /api/dictionaries недоступен, используем локальную копию справочников', err);
      return DICTIONARIES_FALLBACK;
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
// { action, amount?, commentForClient?, reasonCode?, infoItems? }
export const decide = (id, body) => request('POST', `/analyst/applications/${id}/decision`, { body });

// ---------- Демо ----------

export const resetDemo = () => request('POST', '/demo/reset');
