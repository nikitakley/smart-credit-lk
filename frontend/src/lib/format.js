// Неразрывный пробел перед ₽ — знак не отрывается от суммы при переносе
export const formatRub = (n) => `${Math.round(n).toLocaleString('ru-RU')} ₽`;

// 10 000 000 → «10 млн ₽», 300 000 → «300 тыс. ₽» — для условий продуктов
export function formatCompactRub(n) {
  const nb = ' ';
  if (n >= 1_000_000) return `${(n / 1_000_000).toLocaleString('ru-RU', { maximumFractionDigits: 1 })}${nb}млн${nb}₽`;
  if (n >= 1_000) return `${Math.round(n / 1_000).toLocaleString('ru-RU')}${nb}тыс.${nb}₽`;
  return formatRub(n);
}

export const formatDate = (iso) => new Date(iso).toLocaleDateString('ru-RU');

export const formatDateTime = (iso) => new Date(iso).toLocaleString('ru-RU', {
  day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
});

export const formatPercent = (n) => `${n.toLocaleString('ru-RU')}%`;

// plural(5, ['месяц', 'месяца', 'месяцев']) → 'месяцев'
export function plural(n, [one, few, many]) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

export const formatMonths = (n) => `${n} ${plural(n, ['месяц', 'месяца', 'месяцев'])}`;

// Аннуитетный платёж, округлён до 100 ₽
export function annuity(amount, ratePercent, months) {
  const r = ratePercent / 1200;
  const payment = (amount * r) / (1 - (1 + r) ** -months);
  return Math.round(payment / 100) * 100;
}
