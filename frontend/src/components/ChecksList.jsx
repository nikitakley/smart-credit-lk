import Badge from './Badge.jsx';
import { formatAge, formatDate, formatDateTime, formatRub, plural } from '../lib/format.js';

// Проверки банка (checks[]). Порядок в ответе не гарантирован — выводим по источникам.
const ORDER = ['bank', 'egrul', 'nbki', 'pb'];
const STATUS = {
  ok: { tone: 'success', label: 'В порядке' },
  warning: { tone: 'warning', label: 'Есть замечания' },
  fail: { tone: 'error', label: 'Не пройдена' },
  // Источник не ответил — это не ошибка клиента, поэтому нейтрально
  unavailable: { tone: 'info', icon: '↻', label: 'Источник временно недоступен' },
};

const filled = (v) => v != null && v !== '';
const signed = (n) => `${n > 0 ? '+' : ''}${n.toLocaleString('ru-RU')}%`;
const companies = (n) => `${n} ${plural(n, ['компания', 'компании', 'компаний'])}`;

// Сведения details → строки [подпись, значение]; пустые поля пропускаем. Схема — по source и status.
function detailRows(check, unavailableReasons) {
  const d = check.details;
  if (check.status === 'unavailable') {
    const reason = unavailableReasons?.find((r) => r.code === d.reason)?.label ?? d.reason;
    return [['Причина', reason], ['Код ответа источника', d.httpStatus]];
  }
  switch (check.source) {
    case 'bank':
      return [
        ['Поступления на счёт', filled(d.monthlyRevenue) && `${formatRub(d.monthlyRevenue)} в месяц`],
        ['Изменение за 12 месяцев', filled(d.revenueGrowth) && signed(d.revenueGrowth)],
        ['Обороты в банке', filled(d.historyMonths) && formatAge(d.historyMonths)],
      ];
    case 'egrul':
      if (!d.found) return [['Реестр', 'Сведений в реестре нет']];
      return [
        ['Статус', d.statusName ?? d.status],
        ['Дата регистрации', filled(d.registeredAt) && `${formatDate(d.registeredAt)}${filled(d.ageMonths) ? ` · ${formatAge(d.ageMonths)}` : ''}`],
        ['Руководитель', filled(d.head) && [d.head, d.headPosition].filter(filled).join(', ')],
        ['ОГРН', d.ogrn],
        ['ОКВЭД', d.okved],
        ['Адрес', d.address],
      ];
    case 'nbki':
      if (!d.historyFound) return [['Кредитная история', 'В бюро истории нет']];
      return [
        ['Рейтинг бюро', filled(d.bureauScore) && `${d.bureauScore} из 850`],
        ['Платежи по кредитам', filled(d.monthlyPayments) && `${formatRub(d.monthlyPayments)} в месяц`],
        ['Остаток долга', filled(d.totalDebt) && `${formatRub(d.totalDebt)} · кредитов: ${d.activeLoans ?? '—'}`],
        ['Текущая просрочка', filled(d.currentOverdue) && (d.currentOverdue > 0 ? formatRub(d.currentOverdue) : 'нет')],
        ['Просрочки за 24 месяца', filled(d.overdues24m) && (d.overdues24m > 0
          ? `${d.overdues24m}: до 29 дней — ${d.overduesUpTo29 ?? 0}, 30–89 — ${d.overdues30To89 ?? 0}, 90+ — ${d.overdues90Plus ?? 0}`
          : 'нет')],
        ['Кредитная история', filled(d.historyMonths) && formatAge(d.historyMonths)],
        ['Запросов истории за 30 дней', d.inquiriesLastMonth],
      ];
    case 'pb': {
      if (!d.found) return [['Сведения', 'Сведений нет']];
      const risks = [
        d.massAddressCompanies && `массовый адрес — ${companies(d.massAddressCompanies)}`,
        d.massHeadCompanies && `массовый руководитель — ${companies(d.massHeadCompanies)}`,
        d.disqualifiedPersons && 'есть дисквалифицированные лица',
        d.unreliableInfo?.length > 0 && `недостоверные сведения: ${d.unreliableInfo.join(', ')}`,
        d.taxArrears > 0 && `долг по налогам ${formatRub(d.taxArrears)}`,
        d.reportingOverdue && 'не сдаёт отчётность более года',
      ].filter(Boolean);
      return [
        ['Признаки риска', risks.length ? risks.join('; ') : 'не найдены'],
        ['Налоговый режим', d.taxRegime],
        ['Сотрудников', d.employees],
        [`Выручка${filled(d.reportYear) ? ` за ${d.reportYear}` : ''}`, filled(d.revenue) && formatRub(d.revenue)],
        ['Чистая прибыль', filled(d.netProfit) && formatRub(d.netProfit)],
      ];
    }
    default:
      return [];
  }
}

/**
 * Список проверок. Клиент получает проверки без details; аналитик — с details (или null у демо-заявок).
 * withDetails — показывать раскрывающийся блок «Подробнее», unavailableReasons — из справочника.
 */
export default function ChecksList({ checks, withDetails = false, unavailableReasons }) {
  const sorted = [...checks].sort((a, b) => ORDER.indexOf(a.source) - ORDER.indexOf(b.source));
  return (
    <ul className="checks">
      {sorted.map((c) => {
        const s = STATUS[c.status] ?? { tone: 'info', label: c.status };
        const rows = withDetails && c.details ? detailRows(c, unavailableReasons).filter(([, v]) => filled(v) && v !== false) : [];
        return (
          <li key={c.source} className="check-row">
            <div className="check-row__head">
              <div className="check-row__text">
                <b>{c.title}</b>
                <span className="small muted">{c.summary}</span>
                {withDetails && c.fetchedAt && <span className="caption muted">Данные на {formatDateTime(c.fetchedAt)}</span>}
              </div>
              <Badge tone={s.tone} icon={s.icon}>{s.label}</Badge>
            </div>
            {rows.length > 0 && (
              <details className="check-details">
                <summary>Подробнее</summary>
                <dl className="kv-grid kv-grid--2">
                  {rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
                </dl>
              </details>
            )}
          </li>
        );
      })}
    </ul>
  );
}
