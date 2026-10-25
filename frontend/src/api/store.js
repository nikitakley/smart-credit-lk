// Демо-хранилище вместо бэкенда. Формат данных — как в документе «Контракт фронт ↔ бэк».
// Живёт в localStorage, поэтому кабинеты клиента и аналитика в соседних вкладках
// видят одни и те же заявки. Все данные синтетические (ИНН проходят проверку контрольных цифр).
import { annuity } from '../lib/format.js';
import { KEY_RATE, explainDecision, improvementsFor, scoreApplication } from './scoring.js';

const KEY = 'alfa-cabinet-demo-v3'; // при изменении сида — повышать версию
export const CHANGE_EVENT = 'alfa-demo-change';

// finance — синтетическая «выписка» за 12 месяцев: на ней считается скоринг (api/scoring.js)
const company = (c) => ({ status: 'active', kpp: null, source: 'ФНС', fetchedAt: '2026-10-20T10:12:00+03:00', ...c });

export const COMPANIES = Object.fromEntries([
  company({
    inn: '7701000001', type: 'legal', name: 'ООО «Ромашка»', ogrn: '1027700000001', kpp: '770101001', registeredAt: '2024-06-12',
    director: 'Иванов Иван Иванович', okved: { code: '47.19', title: 'Розничная торговля' }, legalAddress: 'г. Москва, ул. Примерная, д. 1, оф. 10',
    phone: '+7 900 000-00-01', email: 'finance@romashka.example', account: '40702810000000000421',
    finance: { monthlyRevenue: 1_600_000, revenueGrowth: 18, loanPayments: 720_000, overdues24m: 0 },
  }),
  company({
    inn: '500100000015', type: 'ip', name: 'ИП Сидоров А. В.', ogrn: '320500000000015', registeredAt: '2020-03-02',
    director: 'Сидоров Алексей Викторович', okved: { code: '43.39', title: 'Отделочные работы' }, legalAddress: 'Московская обл., г. Химки',
    phone: '+7 900 000-00-02', email: 'sidorov@example.com', account: '40802810000000000187',
    finance: { monthlyRevenue: 600_000, revenueGrowth: 5, loanPayments: 90_000, overdues24m: 1 },
  }),
  company({
    inn: '7802000008', type: 'legal', name: 'ООО «Вектор»', ogrn: '1027800000008', kpp: '780201001', registeredAt: '2015-09-21',
    director: 'Петрова Мария Сергеевна', okved: { code: '62.01', title: 'Разработка программного обеспечения' }, legalAddress: 'г. Санкт-Петербург, Невский пр., д. 100',
    phone: '+7 900 000-00-03', email: 'cfo@vector.example', account: '40702810000000000903',
    finance: { monthlyRevenue: 4_200_000, revenueGrowth: 25, loanPayments: 1_200_000, overdues24m: 0 },
  }),
  company({
    inn: '6601000006', type: 'legal', name: 'ООО «Альтаир»', ogrn: '1026600000006', kpp: '660101001', registeredAt: '2023-01-15',
    director: 'Кузнецов Олег Петрович', okved: { code: '49.41', title: 'Грузовые перевозки' }, legalAddress: 'г. Екатеринбург, ул. Заводская, д. 5',
    phone: '+7 900 000-00-04', email: 'office@altair.example', account: '40702810000000000655',
    finance: { monthlyRevenue: 900_000, revenueGrowth: -8, loanPayments: 520_000, overdues24m: 3 },
  }),
  company({
    inn: '7801000005', type: 'legal', status: 'liquidated', name: 'ООО «Старт»', ogrn: '1027800000005', kpp: '780101001', registeredAt: '2018-04-10',
    director: 'Смирнов Павел Андреевич', okved: { code: '56.10', title: 'Рестораны' }, legalAddress: 'г. Санкт-Петербург, ул. Садовая, д. 7',
  }),
].map((c) => [c.inn, c]));

// Ставка «от» = ключевая ставка ЦБ + надбавка за продукт (spread). Итоговая — ещё + надбавка за риск (scoring.js)
const product = (p) => ({ ...p, rateFrom: Math.round((KEY_RATE + p.spread) * 10) / 10 });
export const PRODUCTS = [
  product({ id: 'working-capital', name: 'Оборотный кредит', note: 'Пополнение оборотных средств', minAmount: 300_000, maxAmount: 10_000_000, maxTermMonths: 36, spread: 4.5 }),
  product({ id: 'investment', name: 'Кредит на развитие', note: 'Оборудование, ремонт, расширение', minAmount: 1_000_000, maxAmount: 30_000_000, maxTermMonths: 60, spread: 3.9 }),
  product({ id: 'overdraft', name: 'Овердрафт', note: 'Кассовые разрывы по расчётному счёту', minAmount: 100_000, maxAmount: 5_000_000, maxTermMonths: 12, spread: 5.5 }),
];

// Тестовые учётные записи: клиенты — действующие клиенты банка (регистрация не нужна, FAQ п. 3)
export const TEST_ACCOUNTS = [
  { id: 'romashka', role: 'client', inn: '7701000001', hint: 'Заявка на проверке — пройдите сделку до выдачи' },
  { id: 'vector', role: 'client', inn: '7802000008', hint: 'Заявка одобрена — примите предложение и подпишите договор' },
  { id: 'sidorov', role: 'client', inn: '500100000015', hint: 'ИП, банк запросил документы' },
  { id: 'analyst', role: 'analyst', name: 'Кредитный аналитик', hint: 'Очередь заявок и решения' },
];

export function makeApplication({ id, inn, productId = 'working-capital', amount, termMonths, purpose = 'working_capital', contact, history }) {
  const p = PRODUCTS.find((x) => x.id === productId) ?? PRODUCTS[0];
  const c = COMPANIES[inn];
  const scoring = scoreApplication({ company: c, product: p, amount, termMonths, at: history[0].at });
  return {
    id, company: c, productId: p.id, productName: p.name, amount, termMonths, purpose,
    contact: contact ?? { name: c.director, phone: c.phone, email: c.email },
    status: history.at(-1).status, createdAt: history[0].at, history,
    score: scoring.score, factors: scoring.factors, scoringInputs: scoring.inputs, rateBreakdown: scoring.rateBreakdown,
    aiRecommendation: scoring.recommendation, // сформирована правилами; поле названо по контракту с бэком
    decision: null, offer: null, aiExplanation: null, improvements: [], signing: null, issuance: null,
  };
}

const OUTCOME = { approve: 'approved', counter_offer: 'counter_offer', request_docs: 'docs_requested', reject: 'rejected' };

// action: approve | counter_offer | request_docs | reject — как POST /api/analyst/applications/{id}/decision
export function applyDecision(app, { action, amount, termMonths, rate, commentForClient = '', reasonCode }, now) {
  const status = OUTCOME[action];
  const next = { ...app, status, history: [...app.history, { status, at: now, actor: 'analyst', note: commentForClient || undefined }] };
  if (action === 'request_docs') return next;

  const approvedAmount = action === 'reject' ? null : amount;
  const rec = app.aiRecommendation;
  next.decision = {
    outcome: status, requestedAmount: app.amount, approvedAmount, decidedBy: 'analyst', decidedAt: now,
    commentForClient, reasonCode, followedAi: status === rec.outcome && approvedAmount === rec.amount,
  };
  next.aiExplanation = { text: explainDecision(app, status, approvedAmount), generatedAt: now, source: 'rules' };
  next.improvements = improvementsFor(app, status);
  if (status !== 'rejected') {
    next.offer = {
      type: status, amount, termMonths, rate, rateBreakdown: app.rateBreakdown, monthlyPayment: annuity(amount, rate, termMonths),
      collateralRequired: 'none', validUntil: new Date(Date.parse(now) + 7 * 864e5).toISOString(),
      requested: { amount: app.amount, termMonths: app.termMonths, collateral: 'none' },
    };
  }
  return next;
}

// Клиент принял предложение → договор сформирован и ждёт подписи
export function startSigning(app, now) {
  const contractNumber = `КД-${app.id.replace('A-', '')}/${new Date(now).getFullYear()}`;
  return {
    ...app, status: 'signing', signing: { contractNumber, createdAt: now, code: null },
    history: [...app.history, { status: 'signing', at: now, actor: 'client', note: `Предложение принято, сформирован договор ${contractNumber}` }],
  };
}

// Код подтверждения подписи — в демо показываем в интерфейсе (FAQ: можно без SMS)
export function issueSignCode(app, now) {
  const code = String(100000 + Math.floor(Math.random() * 900000));
  return { ...app, signing: { ...app.signing, code, codeSentAt: now } };
}

// Подписание простой ЭП (демо) и моделируемая выдача на расчётный счёт клиента
export function completeSigning(app, now) {
  const issuance = {
    contractNumber: app.signing.contractNumber, signedAt: now, issuedAt: now,
    amount: app.offer.amount, account: app.company.account,
  };
  return {
    ...app, status: 'issued', issuance, signing: { ...app.signing, code: null, signedAt: now },
    history: [...app.history, { status: 'issued', at: now, actor: 'system', note: `Договор подписан, деньги зачислены на счёт •••• ${app.company.account.slice(-4)}` }],
  };
}

function seed() {
  const at = (s) => `2026-10-${s}:00+03:00`;
  const h = (status, when, actor, note) => ({ status, at: at(when), actor, note });
  const apps = {
    'A-1024': makeApplication({ id: 'A-1024', inn: '7701000001', amount: 2_000_000, termMonths: 24, history: [h('submitted', '20T10:12', 'client'), h('scoring', '20T10:13', 'system', 'Проверяем выписку и данные ФНС')] }),
    'A-1023': makeApplication({ id: 'A-1023', inn: '500100000015', productId: 'overdraft', amount: 500_000, termMonths: 12, purpose: 'cash_gap', history: [h('submitted', '19T15:40', 'client'), h('scoring', '19T15:41', 'system')] }),
    'A-1022': makeApplication({ id: 'A-1022', inn: '7802000008', productId: 'investment', amount: 5_000_000, termMonths: 36, purpose: 'equipment', history: [h('submitted', '19T09:05', 'client'), h('scoring', '19T09:06', 'system')] }),
    'A-1021': makeApplication({ id: 'A-1021', inn: '6601000006', amount: 1_200_000, termMonths: 18, history: [h('submitted', '18T11:20', 'client'), h('scoring', '18T11:21', 'system')] }),
  };
  apps['A-1023'] = applyDecision(apps['A-1023'], { action: 'request_docs', commentForClient: 'Нужна выписка по счёту в другом банке за 12 месяцев' }, at('19T17:05'));
  // Решения аналитика по рекомендациям системы — в очереди видна доля совпадений
  for (const id of ['A-1022', 'A-1021']) {
    const rec = apps[id].aiRecommendation;
    const action = { approved: 'approve', counter_offer: 'counter_offer', rejected: 'reject' }[rec.outcome];
    apps[id] = applyDecision(apps[id], {
      action, amount: rec.amount, termMonths: rec.termMonths, rate: rec.rate,
      commentForClient: action === 'reject' ? 'Долговая нагрузка и просрочки выше допустимых' : '',
      reasonCode: action === 'reject' ? 'debt_load' : undefined,
    }, at(id === 'A-1022' ? '19T16:30' : '18T14:00'));
  }
  return {
    nextNumber: 1025,
    // Текущая заявка каждого клиента — для ссылки «Моя заявка»
    currentByInn: { '7701000001': 'A-1024', '500100000015': 'A-1023', '7802000008': 'A-1022', '6601000006': 'A-1021' },
    applications: apps,
  };
}

let cache = null;

export function readState() {
  if (!cache) {
    try { cache = JSON.parse(localStorage.getItem(KEY)); } catch { cache = null; }
    cache ??= seed();
  }
  return cache;
}

export function writeState(next) {
  cache = next;
  try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* приватный режим — живём в памяти */ }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export const resetState = () => writeState(seed());

// Изменения из соседней вкладки
window.addEventListener('storage', (e) => {
  if (e.key !== KEY) return;
  cache = null;
  window.dispatchEvent(new Event(CHANGE_EVENT));
});
