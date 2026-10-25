// Единая точка доступа к данным. Сейчас ходит в демо-хранилище, при подключении бэка
// меняется только этот файл: сигнатуры повторяют эндпоинты из «Контракт фронт ↔ бэк».
import { isValidInn } from '../lib/inn.js';
import { recommendProducts } from './assistantMock.js';
import {
  CHANGE_EVENT, COMPANIES, PRODUCTS, TEST_ACCOUNTS, applyDecision, completeSigning, issueSignCode,
  makeApplication, readState, resetState, startSigning, writeState,
} from './store.js';

export class ApiError extends Error {
  constructor(code) { super(code); this.code = code; }
}

const delay = (ms = 250) => new Promise((resolve) => setTimeout(resolve, ms));
const clone = (x) => structuredClone(x);
const now = () => new Date().toISOString();

function findApp(state, id) {
  const app = state.applications[id];
  if (!app) throw new ApiError('application_not_found');
  return app;
}

function saveApp(state, app) {
  writeState({ ...state, applications: { ...state.applications, [app.id]: app } });
  return clone(app);
}

// ---------- Вход по тестовым учётным записям ----------
// Сессия в sessionStorage — своя у каждой вкладки: клиент и аналитик работают рядом.
// В промышленной версии — вход через Альфа-ID / ДБО (действующий клиент банка).
const SESSION_KEY = 'alfa-cabinet-session';

export function currentSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY)); } catch { return null; }
}

// GET /api/auth/test-accounts
export async function getTestAccounts() {
  return TEST_ACCOUNTS.map((a) => ({ ...a, name: a.role === 'client' ? COMPANIES[a.inn].name : a.name }));
}

// POST /api/auth/login
export async function login(accountId) {
  await delay(200);
  const acc = TEST_ACCOUNTS.find((a) => a.id === accountId);
  if (!acc) throw new ApiError('account_not_found');
  const session = acc.role === 'client'
    ? { role: 'client', accountId, inn: acc.inn, name: COMPANIES[acc.inn].name }
    : { role: 'analyst', accountId, name: acc.name };
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(session)); } catch { /* без хранилища — вход до перезагрузки не держится */ }
  window.dispatchEvent(new Event(CHANGE_EVENT));
  return session;
}

// POST /api/auth/logout
export async function logout() {
  try { sessionStorage.removeItem(SESSION_KEY); } catch { /* нечего чистить */ }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

// Клиент текущей сессии: компания и его заявка — для шапки и ссылки «Моя заявка»
export async function getClientSession() {
  const session = currentSession();
  if (session?.role !== 'client') return null;
  return { ...session, company: clone(COMPANIES[session.inn]), applicationId: readState().currentByInn[session.inn] ?? null };
}

// ---------- Клиент ----------

// GET /api/companies/{inn}
export async function getCompany(inn) {
  await delay(600);
  if (!isValidInn(inn)) throw new ApiError('invalid_inn');
  const company = COMPANIES[inn];
  if (!company) throw new ApiError('company_not_found');
  if (company.status !== 'active') throw new ApiError('company_inactive');
  return clone(company);
}

// GET /api/products
export async function getProducts() {
  await delay();
  return clone(PRODUCTS);
}

// POST /api/assistant/recommend — { purpose, amount, termMonths, collateral } → { summary, items[] }
export async function recommend(input) {
  await delay(700);
  return clone(recommendProducts(input));
}

// POST /api/applications — заявка от компании текущей сессии
export async function createApplication({ productId, amount, termMonths, purpose, contact }) {
  await delay();
  const session = currentSession();
  if (session?.role !== 'client') throw new ApiError('unauthorized');
  const state = readState();
  const id = `A-${state.nextNumber}`;
  const at = now();
  const app = makeApplication({
    id, inn: session.inn, productId, amount, termMonths, purpose, contact,
    history: [{ status: 'submitted', at, actor: 'client' }, { status: 'scoring', at, actor: 'system', note: 'Проверяем выписку и данные ФНС' }],
  });
  writeState({
    ...state, nextNumber: state.nextNumber + 1,
    currentByInn: { ...state.currentByInn, [session.inn]: id },
    applications: { ...state.applications, [id]: app },
  });
  return { id };
}

// GET /api/applications/{id} (для демо сразу с решением, факторами и оффером)
export async function getApplication(id) {
  await delay();
  return clone(findApp(readState(), id));
}

// POST /api/applications/{id}/offer/accept — договор сформирован, ждёт подписи
export async function acceptOffer(id) {
  await delay();
  const state = readState();
  const app = findApp(state, id);
  if (!app.offer || !['approved', 'counter_offer'].includes(app.status)) throw new ApiError('no_offer');
  return saveApp(state, startSigning(app, now()));
}

// POST /api/applications/{id}/offer/decline
export async function declineOffer(id) {
  await delay();
  const state = readState();
  const app = findApp(state, id);
  if (!app.offer) throw new ApiError('no_offer');
  const status = 'declined_by_client';
  return saveApp(state, { ...app, status, history: [...app.history, { status, at: now(), actor: 'client' }] });
}

// POST /api/applications/{id}/sign/code — в демо код возвращается в ответе и показывается в интерфейсе.
// В промышленной версии — SMS / push в приложении банка.
export async function requestSignCode(id) {
  await delay(500);
  const state = readState();
  const app = findApp(state, id);
  if (app.status !== 'signing') throw new ApiError('not_signing');
  const next = issueSignCode(app, now());
  saveApp(state, next);
  return { code: next.signing.code, sentAt: next.signing.codeSentAt };
}

// POST /api/applications/{id}/sign — подписание простой ЭП и моделируемая выдача
export async function signContract(id, code) {
  await delay(700);
  const state = readState();
  const app = findApp(state, id);
  if (app.status !== 'signing') throw new ApiError('not_signing');
  if (!app.signing.code || code !== app.signing.code) throw new ApiError('invalid_code');
  return saveApp(state, completeSigning(app, now()));
}

// ---------- Аналитик ----------

// GET /api/analyst/applications
export async function listApplications() {
  await delay();
  return Object.values(readState().applications)
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
    .map(clone);
}

// POST /api/analyst/applications/{id}/decision
export async function decide(id, input) {
  await delay();
  const state = readState();
  return saveApp(state, applyDecision(findApp(state, id), input, now()));
}

export async function resetDemo() {
  resetState();
}
