// [ASM] Статусы заявки — по документу «Контракт фронт ↔ бэк», финально СОГЛАСОВАТЬ С БЭКЕНДОМ (Никита).
// При изменениях правится только этот файл: таймлайн и бейджи берут всё отсюда.
// tone — вариант бейджа/маркера: success | warning | info | error
import { formatDateTime } from '../lib/format.js';

export const STATUS = {
  submitted:          { label: 'Заявка подана',       tone: 'info' },
  scoring:            { label: 'Проверяем данные',    tone: 'info' },
  docs_requested:     { label: 'Нужны документы',     tone: 'warning' },
  approved:           { label: 'Одобрено',            tone: 'success' },
  counter_offer:      { label: 'Контрпредложение',    tone: 'warning' },
  rejected:           { label: 'Отказ',               tone: 'error' },
  signing:            { label: 'Подписание договора', tone: 'info' },
  issued:             { label: 'Кредит выдан',        tone: 'success' },
  declined_by_client: { label: 'Клиент отказался',    tone: 'info' },
};

export const ACTORS = { client: 'клиент', system: 'система', analyst: 'аналитик' };

// Основной путь заявки: по нему таймлайн показывает ещё не пройденные шаги
export const FLOW = ['submitted', 'scoring', 'approved', 'signing', 'issued'];

// Статусы вне основного пути и место, которое они занимают на нём
const FLOW_POSITION = { docs_requested: 1, counter_offer: 2 };

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
