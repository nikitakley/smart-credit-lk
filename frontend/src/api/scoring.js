// Скоринг на детерминированных правилах. По FAQ организаторов ML/LLM не обязательны,
// но логика должна быть прозрачной: по каким входным данным и почему получен результат.
// Каждое число в объяснениях клиенту и аналитику считается здесь из финансов компании.
// На бэке — тот же алгоритм (или модель с тем же форматом ответа: score, factors, recommendation).
import { annuity, formatMonths, formatPercent, formatRub, plural } from '../lib/format.js';

export const KEY_RATE = 14;          // ключевая ставка ЦБ на 22.10.2026 (cbr.ru) — обновить перед демо
export const DTI_LIMIT = 0.5;        // [ASM] платежи по всем кредитам — не больше 50% среднемесячной выручки
export const MIN_SCORE = 450;        // [ASM] ниже — отказ
const BASE_SCORE = 560;              // [ASM] стартовая оценка до учёта факторов
// [ASM] надбавка к ставке за риск по оценке
const RISK_PREMIUM = [{ min: 700, add: 0 }, { min: 550, add: 1 }, { min: 0, add: 2.5 }];

const pct = (x) => Math.round(x * 100);
const lowerFirst = (s) => s.charAt(0).toLowerCase() + s.slice(1);
const round1 = (x) => Math.round(x * 10) / 10;

function monthsBetween(fromIso, toIso) {
  const a = new Date(fromIso);
  const b = new Date(toIso);
  return (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth());
}

export function formatAge(months) {
  const y = Math.floor(months / 12);
  const m = months % 12;
  const parts = [];
  if (y) parts.push(`${y} ${plural(y, ['год', 'года', 'лет'])}`);
  if (m) parts.push(`${m} ${plural(m, ['месяц', 'месяца', 'месяцев'])}`);
  return parts.join(' ') || 'меньше месяца';
}

// Максимальная сумма кредита при заданном ежемесячном платеже (обратный аннуитет)
function maxPrincipal(payment, ratePercent, months) {
  const r = ratePercent / 1200;
  return (payment * (1 - (1 + r) ** -months)) / r;
}

// Правила: каждый фактор — баллы к оценке + понятная формулировка с цифрой из данных
function factorRules(f, ageMonths) {
  const dti = f.loanPayments / f.monthlyRevenue;
  const debt = dti <= 0.2 ? { points: 120, label: 'Низкая долговая нагрузка' }
    : dti <= 0.35 ? { points: 40, label: 'Умеренная долговая нагрузка' }
    : dti <= DTI_LIMIT ? { points: -80, label: 'Высокая долговая нагрузка' }
    : { points: -160, label: 'Долговая нагрузка выше лимита' };

  const g = f.revenueGrowth;
  const revenue = g >= 10 ? { points: 120, label: 'Растущая выручка', detail: `Выручка за 12 месяцев выросла на ${g}%` }
    : g >= 0 ? { points: 50, label: 'Стабильная выручка', detail: `Выручка за 12 месяцев изменилась на +${g}%` }
    : { points: -100, label: 'Падение выручки', detail: `Выручка за 12 месяцев снизилась на ${Math.abs(g)}%` };

  const o = f.overdues24m;
  const history = o === 0 ? { points: 80, label: 'Нет просрочек', detail: 'Кредитная история без просрочек за 2 года' }
    : o === 1 ? { points: -20, label: 'Единичная просрочка', detail: '1 просрочка до 30 дней за 2 года' }
    : { points: -120, label: 'Просрочки по кредитам', detail: `${o} ${plural(o, ['просрочка', 'просрочки', 'просрочек'])} за 2 года` };

  const age = ageMonths >= 36 ? { points: 60, label: 'Бизнес работает давно' }
    : ageMonths >= 12 ? { points: 0, label: 'Срок работы бизнеса' }
    : { points: -80, label: 'Молодой бизнес' };

  return [
    { code: 'debt_load', ...debt, detail: `Платежи по текущим кредитам — ${pct(dti)}% выручки (лимит ${pct(DTI_LIMIT)}%)` },
    { code: 'revenue_trend', ...revenue },
    { code: 'credit_history', ...history },
    { code: 'business_age', ...age, detail: formatAge(ageMonths) },
  ];
}

const weightOf = (points) => (Math.abs(points) >= 100 ? 'high' : Math.abs(points) >= 50 ? 'medium' : 'low');
const impactOf = (points) => (points > 0 ? 'positive' : points < 0 ? 'negative' : 'neutral');

/**
 * Скоринг заявки. company.finance — синтетические данные выписки, product — из PRODUCTS.
 * Возвращает всё, что видят аналитик и клиент: score, factors, ставку с разбивкой и рекомендацию.
 */
export function scoreApplication({ company, product, amount, termMonths, at }) {
  const f = company.finance;
  const ageMonths = monthsBetween(company.registeredAt, at);
  const rules = factorRules(f, ageMonths);

  const value = Math.max(0, Math.min(1000, BASE_SCORE + rules.reduce((s, r) => s + r.points, 0)));
  const factors = rules
    .map((r) => ({ code: r.code, label: r.label, detail: r.detail, impact: impactOf(r.points), weight: weightOf(r.points), points: r.points }))
    .sort((a, b) => Math.abs(b.points) - Math.abs(a.points));

  const premium = RISK_PREMIUM.find((p) => value >= p.min).add;
  const rate = round1(product.rateFrom + premium);
  const rateBreakdown = { keyRate: KEY_RATE, productSpread: round1(product.rateFrom - KEY_RATE), riskPremium: premium, rate };

  // Сколько ещё можно платить, не превышая лимит нагрузки, и какую сумму это покрывает
  const freePayment = f.monthlyRevenue * DTI_LIMIT - f.loanPayments;
  const affordable = freePayment > 0 ? Math.floor(maxPrincipal(freePayment, rate, termMonths) / 100_000) * 100_000 : 0;
  const cap = Math.min(affordable, product.maxAmount);
  const dtiWith = (sum) => pct((f.loanPayments + annuity(sum, rate, termMonths)) / f.monthlyRevenue);

  let recommendation;
  if (value < MIN_SCORE || cap < product.minAmount) {
    const reason = value < MIN_SCORE
      ? `оценка ${value} ниже порога ${MIN_SCORE}`
      : `свободной выручки не хватает даже на минимальную сумму ${formatRub(product.minAmount)}`;
    recommendation = { outcome: 'rejected', amount: null, termMonths, rate, text: `Отказ: ${reason}. Главный фактор — ${factors[0].label.toLowerCase()}.` };
  } else if (amount <= cap) {
    recommendation = {
      outcome: 'approved', amount, termMonths, rate,
      text: `Одобрить ${formatRub(amount)} на ${formatMonths(termMonths)} под ${formatPercent(rate)}: с новым платежом нагрузка — ${dtiWith(amount)}% выручки, в пределах лимита ${pct(DTI_LIMIT)}%.`,
    };
  } else {
    recommendation = {
      outcome: 'counter_offer', amount: cap, termMonths, rate,
      text: `Контрпредложение: ${formatRub(cap)} вместо ${formatRub(amount)}. С запрошенной суммой платежи по кредитам заняли бы ${dtiWith(amount)}% выручки при лимите ${pct(DTI_LIMIT)}%.`,
    };
  }

  return {
    score: { value, max: 1000, minScore: MIN_SCORE },
    factors,
    rateBreakdown,
    recommendation,
    inputs: { ...f, ageMonths, dtiNow: pct(f.loanPayments / f.monthlyRevenue), dtiWithRequested: dtiWith(amount), affordable },
  };
}

/** Объяснение решения клиенту — из тех же данных, что и рекомендация, без шаблонных фраз. */
export function explainDecision(app, outcome, approvedAmount) {
  const { factors, scoringInputs: inputs } = app;
  const plus = factors.find((x) => x.impact === 'positive');
  const minus = factors.find((x) => x.impact === 'negative');
  if (outcome === 'approved') {
    const lead = plus ? `Главный плюс — ${plus.label.toLowerCase()}: ${lowerFirst(plus.detail)}.` : 'Показатели в норме.';
    const load = inputs.dtiWithRequested <= pct(DTI_LIMIT)
      ? `С новым кредитом платежи займут ${inputs.dtiWithRequested}% выручки — в пределах лимита ${pct(DTI_LIMIT)}%.`
      : `С новым кредитом платежи займут ${inputs.dtiWithRequested}% выручки — выше лимита ${pct(DTI_LIMIT)}%, но аналитик одобрил заявку с учётом других показателей.`;
    return `Заявку одобрили. ${lead} ${load}`;
  }
  if (outcome === 'counter_offer') {
    return `Сумму снизили до ${formatRub(approvedAmount)}: с ${formatRub(app.amount)} платежи по всем кредитам заняли бы ${inputs.dtiWithRequested}% выручки при лимите ${pct(DTI_LIMIT)}%. Если погасить часть текущих кредитов или добавить залог, сумму можно пересмотреть.`;
  }
  const main = minus ?? factors[0];
  return `Главная причина — ${main.label.toLowerCase()}: ${lowerFirst(main.detail)}. Снизьте нагрузку и подайте заявку повторно.`;
}

/** Что изменить, чтобы условия стали лучше — тоже от факторов. */
export function improvementsFor(app, outcome) {
  if (outcome === 'approved') return [];
  const list = [];
  const has = (code) => app.factors.some((x) => x.code === code && x.impact === 'negative');
  if (has('debt_load')) list.push(`Погасить часть текущих кредитов: лимит нагрузки — ${pct(DTI_LIMIT)}% выручки`);
  if (has('credit_history')) list.push('Не допускать новых просрочек в ближайшие 6 месяцев');
  if (has('revenue_trend')) list.push('Подать заявку после восстановления выручки');
  list.push('Добавить залог или поручительство');
  list.push('Перевести обороты на счёт в Альфа-Банке — банк увидит выручку точнее');
  return list;
}
