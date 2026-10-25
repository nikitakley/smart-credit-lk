import { useParams } from 'react-router-dom';
import { StatusBadge } from '../../components/Badge.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import Page from '../../components/Page.jsx';
import StatusTimeline from '../../components/StatusTimeline.jsx';
import RingGauge from '../../components/art/RingGauge.jsx';
import { getApplication } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { buildTimeline } from '../../config/statuses.js';
import { decisionHeadline } from '../../lib/decision.js';
import { formatDateTime, formatRub } from '../../lib/format.js';

export default function ApplicationStatus() {
  const { id } = useParams();
  const { data: app, error } = useLoad(() => getApplication(id), [id]);

  if (error) return <Page title="Заявка не найдена" subtitle={`Проверьте номер: ${id}`} />;
  if (!app) return <Page title={`Заявка № ${id}`} subtitle="Загружаем заявку…" />;

  const steps = buildTimeline(app.history);
  const passed = steps.filter((s) => s.state !== 'upcoming').length;
  const lastNote = app.history.at(-1).note;

  return (
    <Page
      title={`Заявка № ${app.id}`}
      subtitle={`${app.company.name} · ${app.productName} · запрошено ${formatRub(app.amount)} на ${app.termMonths} мес.`}
      extra={<StatusBadge status={app.status} />}
      art={(
        <RingGauge
          ratio={passed / steps.length}
          value={`${passed}/${steps.length}`}
          caption="этапов пройдено"
          tone={app.status === 'issued' ? 'aqua' : 'red'}
        />
      )}
    >
      <div className="grid-2">
        <Card>
          <h2 className="section-title">Статус</h2>
          <StatusTimeline steps={steps} />
        </Card>
        <Card className="stack">
          {app.issuance ? (
            <>
              <h3>Кредит выдан</h3>
              <div className="display-sm"><span className="fundament">{formatRub(app.issuance.amount)}</span></div>
              <dl className="kv-grid kv-grid--1">
                <div><dt>Договор</dt><dd>{app.issuance.contractNumber}, подписан {formatDateTime(app.issuance.signedAt)}</dd></div>
                <div><dt>Зачислено</dt><dd>На расчётный счёт •••• {app.issuance.account.slice(-4)}</dd></div>
              </dl>
              <p className="muted small m0">Выдача смоделирована: реальных проводок нет.</p>
            </>
          ) : app.status === 'signing' ? (
            <>
              <h3>Осталось подписать договор</h3>
              <p className="m0">{decisionHeadline(app.decision)}. Договор {app.signing.contractNumber} готов.</p>
              <Button to={`/applications/${app.id}/sign`}>Подписать договор</Button>
            </>
          ) : (
            <h3>Решение</h3>
          )}
          {app.issuance || app.status === 'signing' ? null : app.decision ? (
            <>
              <p className="m0">{decisionHeadline(app.decision)}</p>
              <Button to={`/applications/${app.id}/decision`} variant="secondary">Почему такое решение</Button>
              {app.offer && <Button to={`/applications/${app.id}/offer`}>Предложение банка</Button>}
            </>
          ) : app.status === 'docs_requested' ? (
            <>
              <p className="m0">{lastNote ?? 'Банку нужны дополнительные документы.'}</p>
              <p className="muted small m0">Загрузка документов — после согласования с бэком.</p>
            </>
          ) : (
            <p className="muted small m0">Появится после проверки. Обычно это занимает до одного рабочего дня.</p>
          )}
        </Card>
      </div>
    </Page>
  );
}
