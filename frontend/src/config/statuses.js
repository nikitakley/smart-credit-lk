// Статусы заявки — как ApplicationStatus в docs/api/openapi.json.
// При изменениях правится только этот файл: таймлайн, бейджи и фильтры берут всё отсюда.
// tone — вариант бейджа/маркера: success | warning | info | error
import { formatDateTime } from '../lib/format.js';

export const STATUS = {
  draft:              { label: 'Черновик',                  tone: 'info' },
  submitted:          { label: 'Заявка подана',             tone: 'info' },
  validation:         { label: 'Проверяем анкету',          tone: 'info' },
  enrichment:         { label: 'Запрашиваем сведения',      tone: 'info' },
  scoring:            { label: 'Оцениваем заявку',          tone: 'info' },
  manual_review:      { label: 'На проверке у специалиста', tone: 'info' },
  docs_requested:     { label: 'Нужна информация',          tone: 'warning' },
  approved:           { label: 'Одобрено',                  tone: 'success' },
  counter_offer:      { label: 'Контрпредложение',          tone: 'warning' },
  rejected:           { label: 'Отказ',                     tone: 'error' },
  signing:            { label: 'Подписание договора',       tone: 'info' },
  issued:             { label: 'Кредит выдан',              tone: 'success' },
  declined_by_client: { label: 'Клиент отказался',          tone: 'info' },
};

export const ACTORS = { client: 'клиент', system: 'система', analyst: 'аналитик' };

// Заявка в обработке у банка (конвейер ещё работает)
export const IN_PROGRESS = ['submitted', 'validation', 'enrichment', 'scoring'];
// Решение аналитика бэкенд принимает только в этих статусах
export const ANALYST_DECIDES = ['manual_review', 'docs_requested'];
// Повторный запрос данных из источников бэкенд разрешает только в этих статусах (иначе 409)
export const CHECKS_REFRESH = ['enrichment', 'scoring', 'manual_review', 'docs_requested'];

// Основной путь заявки: по нему таймлайн показывает ещё не пройденные шаги
export const FLOW = ['submitted', 'validation', 'enrichment', 'scoring', 'approved', 'signing', 'issued'];

// Статусы вне основного пути и место, которое они занимают на нём
const FLOW_POSITION = { manual_review: 3, docs_requested: 3, counter_offer: 4 };

// После этих статусов будущих шагов нет
export const TERMINAL = ['rejected', 'issued', 'declined_by_client'];

/**
 * История заявки → шаги для <StatusTimeline>.
 * history: [{ status, at, actor?, note? }] в хронологическом порядке.
 */
export function buildTimeline(history, flow = FLOW) {
  const last = history.at(-1)?.status;

  const passed = history.map((h, i) => {
    const isLast = i === history.length - 1;
    const tone = STATUS[h.status]?.tone;
    let state = 'done';
    if (isLast && tone === 'error') state = 'error';
    else if (isLast && tone === 'warning') state = 'warning';
    else if (isLast && !TERMINAL.includes(h.status)) state = 'current';
    return { key: h.status, label: STATUS[h.status]?.label ?? h.status, date: formatDateTime(h.at), note: h.note, state };
  });

  if (TERMINAL.includes(last)) return passed;

  const position = (s) => (flow.includes(s) ? flow.indexOf(s) : FLOW_POSITION[s] ?? -1);
  const reached = Math.max(-1, ...history.map((h) => position(h.status)));
  const upcoming = flow.slice(reached + 1).map((key) => ({ key, label: STATUS[key].label, state: 'upcoming' }));

  return [...passed, ...upcoming];
}
