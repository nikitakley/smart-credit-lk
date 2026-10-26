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

// Ждём специалиста или действие клиента в другой вкладке
const WAITING = ['manual_review', 'docs_requested', 'approved', 'counter_offer'];

/**
 * Интервал опроса карточки заявки, мс (договорённость с бэкендом, этап 3):
 * в работе у конвейера — 2,5 с первую минуту, затем 10 с; ждём специалиста или клиента — 15 с;
 * draft, signing и конечные статусы меняет только сам пользователь — не опрашиваем (null).
 */
export function applicationPollMs(status, msInStatus) {
  if (IN_PROGRESS.includes(status)) return msInStatus < 60000 ? 2500 : 10000;
  if (WAITING.includes(status)) return 15000;
  return null;
}

/**
 * История заявки → шаги для <StatusTimeline>.
 * history: [{ kind?, status, at, actor?, note? }] в хронологическом порядке.
 * kind: status_changed — шаг процесса; checks_refreshed и любой другой вид — отметка (marks) внутри
 * текущего шага, статус не дублируется. Нет kind — старый формат, считаем сменой статуса.
 */
export function buildTimeline(history, flow = FLOW) {
  const steps = [];
  const pendingMarks = [];
  for (const h of history) {
    const mark = { date: formatDateTime(h.at), note: h.note, actor: ACTORS[h.actor] };
    if (h.kind && h.kind !== 'status_changed') {
      if (steps.length) steps.at(-1).marks.push(mark);
      else pendingMarks.push(mark);
      continue;
    }
    steps.push({
      key: h.status, status: h.status, label: STATUS[h.status]?.label ?? h.status,
      date: formatDateTime(h.at), note: h.note, marks: steps.length ? [] : pendingMarks,
    });
  }

  const last = steps.at(-1)?.status;
  const passed = steps.map((step, i) => {
    const isLast = i === steps.length - 1;
    const tone = STATUS[step.status]?.tone;
    let state = 'done';
    if (isLast && tone === 'error') state = 'error';
    else if (isLast && tone === 'warning') state = 'warning';
    else if (isLast && !TERMINAL.includes(step.status)) state = 'current';
    return { ...step, state };
  });

  if (TERMINAL.includes(last)) return passed;

  const position = (st) => (flow.includes(st) ? flow.indexOf(st) : FLOW_POSITION[st] ?? -1);
  const reached = Math.max(-1, ...steps.map((st) => position(st.status)));
  const upcoming = flow.slice(reached + 1).map((key) => ({ key, label: STATUS[key].label, state: 'upcoming' }));

  return [...passed, ...upcoming];
}
