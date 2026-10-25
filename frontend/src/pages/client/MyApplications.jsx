import { Link } from 'react-router-dom';
import { StatusBadge } from '../../components/Badge.jsx';
import Button from '../../components/Button.jsx';
import Page from '../../components/Page.jsx';
import ArtDocument from '../../components/art/ArtDocument.jsx';
import { listMyApplications } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { formatDate, formatRub } from '../../lib/format.js';

// Заявки компании: черновики продолжаются в мастере, остальные открываются на странице статуса
export default function MyApplications() {
  const { data: apps, error } = useLoad(listMyApplications, [], { pollMs: 15000 });

  return (
    <Page
      title="Мои заявки"
      subtitle="Черновики, заявки на рассмотрении и решения банка — в одном списке."
      actions={<Button to="/apply" variant="ondark" size="l">Новая заявка</Button>}
      art={<ArtDocument />}
    >
      <section className="section">
        {error && <p className="caveat">{error.message}</p>}
        {!apps && !error && <p className="muted">Загружаем заявки…</p>}
        {apps?.length === 0 && <p className="muted">Заявок пока нет — начните с подбора кредита или оформите новую.</p>}
        <ul className="queue">
          {(apps ?? []).map((a) => {
            const draft = a.status === 'draft';
            return (
              <li key={a.id}>
                <Link to={draft ? `/apply?draft=${a.id}` : `/applications/${a.id}`} className="queue-row queue-row--client">
                  <span className="queue-row__main">
                    <b>{a.productName ?? 'Продукт не выбран'}</b>
                    <span className="small muted">{a.id} · обновлена {formatDate(a.updatedAt)}</span>
                  </span>
                  <span className="queue-row__fact"><span className="caption muted">Сумма</span><b>{formatRub(a.amount)}</b></span>
                  <span className="queue-row__fact"><span className="caption muted">Срок</span>{a.termMonths ? `${a.termMonths} мес.` : '—'}</span>
                  <StatusBadge status={a.status} />
                  <span className="queue-row__arrow" aria-hidden="true">{draft ? 'Продолжить →' : '→'}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </section>
    </Page>
  );
}
