import { formatCompactRub, formatPercent } from '../lib/format.js';

// Ключевые условия продукта — как «Сумма / Срок / Ставка» в списке продуктов на alfabank.ru
export default function ProductFacts({ product: p, large = false }) {
  return (
    <dl className={`facts ${large ? 'facts--lg' : ''}`}>
      <div><dt>Сумма</dt><dd>до {formatCompactRub(p.maxAmount)}</dd></div>
      <div><dt>Срок</dt><dd>до {p.maxTermMonths} мес.</dd></div>
      <div><dt>Ставка</dt><dd>от {formatPercent(p.rateFrom)}</dd></div>
    </dl>
  );
}
