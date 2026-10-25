import { STATUS } from '../config/statuses.js';

// Иконка обязательна: красный — и бренд, и ошибка, поэтому статус не передаём только цветом
const ICONS = { success: '✓', warning: '!', info: '•', error: '✕' };

export default function Badge({ tone = 'info', icon = ICONS[tone], children }) {
  return (
    <span className={`badge badge--${tone}`}>
      <span aria-hidden="true">{icon}</span>
      {children}
    </span>
  );
}

export function StatusBadge({ status }) {
  const s = STATUS[status] ?? { label: status, tone: 'info' };
  return <Badge tone={s.tone}>{s.label}</Badge>;
}
