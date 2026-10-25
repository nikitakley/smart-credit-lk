// Заглушка помощника подбора — на бэке её заменит ответ модели (POST /api/assistant/recommend).
// Подбирает до 3 продуктов: сначала по цели, затем отсеивает те, чьи лимиты не подходят.
import { formatMonths, formatRub } from '../lib/format.js';
import { PRODUCTS } from './store.js';

export const PURPOSES = {
  working_capital: 'пополнить оборотные средства',
  cash_gap: 'закрыть кассовый разрыв',
  equipment: 'купить оборудование или транспорт',
  renovation: 'ремонт или расширение',
};

// Какие продукты лучше подходят под цель, по убыванию
const PREFERENCE = {
  working_capital: ['working-capital', 'overdraft', 'investment'],
  cash_gap: ['overdraft', 'working-capital'],
  equipment: ['investment', 'working-capital'],
  renovation: ['investment', 'working-capital'],
};

const WHY = {
  'working-capital': 'Деньги приходят одной суммой — на закупки, зарплаты и налоги, гасите равными платежами.',
  overdraft: 'Деньги доступны сразу, когда на счёте не хватает, — удобно для коротких разрывов.',
  investment: 'Рассчитан на крупные вложения: длинный срок и ставка ниже, чем у оборотного кредита.',
};

function limitIssues(p, amount, termMonths) {
  const issues = [];
  if (amount > p.maxAmount) issues.push(`лимит ${formatRub(p.maxAmount)}`);
  if (amount < p.minAmount) issues.push(`минимальная сумма ${formatRub(p.minAmount)}`);
  if (termMonths > p.maxTermMonths) issues.push(`срок до ${formatMonths(p.maxTermMonths)}`);
  return issues;
}

export function recommendProducts({ purpose, amount, termMonths, collateral }) {
  const candidates = (PREFERENCE[purpose] ?? PRODUCTS.map((p) => p.id))
    .map((id) => PRODUCTS.find((p) => p.id === id))
    .map((product) => ({ product, issues: limitIssues(product, amount, termMonths) }));

  const fitting = candidates.filter((c) => c.issues.length === 0);
  // Если не подходит ничего — показываем ближайший по цели вариант с оговоркой
  const picked = (fitting.length ? fitting : candidates.slice(0, 1)).slice(0, 3);

  const items = picked.map(({ product, issues }, i) => {
    const reasons = [WHY[product.id]];
    if (!issues.length) reasons.push(`Сумма ${formatRub(amount)} и срок ${formatMonths(termMonths)} укладываются в условия.`);
    if (collateral !== 'none') reasons.push('Залог повышает шансы на одобрение полной суммы.');
    return {
      product,
      best: i === 0 && !issues.length,
      reasons,
      caveat: issues.length ? `Подходит не полностью: ${issues.join(', ')}.` : null,
    };
  });

  const best = items.find((i) => i.best);
  const summary = best
    ? `Чтобы ${PURPOSES[purpose]}, лучше всего подойдёт «${best.product.name}».${items.length > 1 ? ' Ниже — ещё варианты, если захотите сравнить.' : ''}`
    : 'Ни один продукт не подходит полностью. Посмотрите ближайший вариант или уменьшите сумму и срок.';

  return { summary, items };
}
