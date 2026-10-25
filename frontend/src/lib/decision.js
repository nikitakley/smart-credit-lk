import { formatRub } from './format.js';

// Заголовок решения банка: «Одобрено 1 500 000 ₽ вместо 2 000 000 ₽»
export function decisionHeadline(decision) {
  if (decision.outcome === 'rejected') return 'В кредите отказано';
  if (decision.outcome === 'counter_offer') {
    return `Одобрено ${formatRub(decision.approvedAmount)} вместо ${formatRub(decision.requestedAmount)}`;
  }
  return `Одобрено ${formatRub(decision.approvedAmount)}`;
}

export const DECISION_LEAD = {
  approved: 'Заявка одобрена полностью. Ниже — факторы, которые повлияли на решение, в порядке важности.',
  counter_offer: 'Банк готов выдать кредит на меньшую сумму. Ниже — факторы, которые повлияли на решение, в порядке важности.',
  rejected: 'Ниже — факторы, которые повлияли на решение, и что можно сделать, чтобы его изменить.',
};
