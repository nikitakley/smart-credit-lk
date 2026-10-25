import { useState } from 'react';
import { Link } from 'react-router-dom';
import Avatar from '../../components/Avatar.jsx';
import { StatusBadge } from '../../components/Badge.jsx';
import Button from '../../components/Button.jsx';
import Page from '../../components/Page.jsx';
import ArtAnalyst from '../../components/art/ArtAnalyst.jsx';
import { listApplications, resetDemo } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { IN_PROGRESS } from '../../config/statuses.js';
import { formatDate, formatRub } from '../../lib/format.js';

// Строки очереди — AnalystQueueItem: решение приходит как decisionOutcome / decidedBy / followedSystem
const FILTERS = [
  { key: 'all', label: 'Все', test: () => true },
  { key: 'review', label: 'На проверке у специалиста', test: (a) => a.status === 'manual_review' },
  { key: 'progress', label: 'В обработке', test: (a) => IN_PROGRESS.includes(a.status) },
  { key: 'docs', label: 'Нужна информация', test: (a) => a.status === 'docs_requested' },
  { key: 'decided', label: 'С решением', test: (a) => !!a.decisionOutcome },
];

function stats(apps) {
  // Совпадение считаем только по решениям специалиста — автоматические решения совпадают всегда
  const byAnalyst = apps.filter((a) => a.decidedBy === 'analyst' && a.followedSystem != null);
  const followed = byAnalyst.filter((a) => a.followedSystem).length;
  return [
    { label: 'Ждут решения', value: apps.filter((a) => a.status === 'manual_review').length },
    { label: 'В обработке', value: apps.filter((a) => IN_PROGRESS.includes(a.status)).length },
    { label: 'Ждут ответа клиента', value: apps.filter((a) => a.status === 'docs_requested').length },
    { label: 'Решений совпало с рекомендацией', value: byAnalyst.length ? `${Math.round((followed / byAnalyst.length) * 100)}%` : '—' },
  ];
}

export default function Queue() {
  const { data: apps, error } = useLoad(() => listApplications(), [], { pollMs: 15000 });
  const [filter, setFilter] = useState('all');
  const active = FILTERS.find((f) => f.key === filter);
  const shown = (apps ?? []).filter(active.test);

  return (
    <Page
      title="Очередь заявок"
      subtitle="Проверьте данные компании и рекомендацию скоринга — решение принимаете вы. Клиент увидит его сразу."
      extra={apps && (
        <div className="hero-stats">
          {stats(apps).map((s) => (
            <div key={s.label} className="hero-stat">
              <div className="hero-stat__value">{s.value}</div>
              <div className="hero-stat__label">{s.label}</div>
            </div>
          ))}
        </div>
      )}
      art={<ArtAnalyst />}
    >
      <section className="section">
        <div className="toolbar">
          <h2>Заявки</h2>
          <div className="chips" role="group" aria-label="Фильтр заявок">
            {FILTERS.map((f) => (
              <button key={f.key} type="button" className="chip" aria-pressed={filter === f.key} onClick={() => setFilter(f.key)}>
                {f.label}
                {apps && <span className="chip__count">{apps.filter(f.test).length}</span>}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="caveat">{error.message}</p>}
        {!apps && !error && <p className="muted">Загружаем…</p>}
        <ul className="queue">
          {shown.map((a) => (
            <li key={a.id}>
              <Link to={`/analyst/applications/${a.id}`} className="queue-row">
                <Avatar name={a.company.name} light />
                <span className="queue-row__main">
                  <b>{a.company.name}</b>
                  <span className="small muted">{a.id} · ИНН {a.company.inn}{a.productName ? ` · ${a.productName}` : ''}</span>
                </span>
                <span className="queue-row__fact"><span className="caption muted">Сумма</span><b>{formatRub(a.amount)}</b></span>
                <span className="queue-row__fact"><span className="caption muted">Подана</span>{a.submittedAt ? formatDate(a.submittedAt) : '—'}</span>
                <StatusBadge status={a.status} />
                <span className="queue-row__arrow" aria-hidden="true">→</span>
              </Link>
            </li>
          ))}
        </ul>
        {apps && shown.length === 0 && <p className="muted">В этом фильтре заявок нет.</p>}

        <div className="row" style={{ marginTop: 'var(--space-6)' }}>
          <Button variant="secondary" size="s" onClick={resetDemo}>Сбросить демо-данные</Button>
        </div>
      </section>
    </Page>
  );
}
