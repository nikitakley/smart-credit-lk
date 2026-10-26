import { useParams } from 'react-router-dom';
import AiHint from '../../components/AiHint.jsx';
import { StatusBadge } from '../../components/Badge.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import FactorList, { FactorLegend } from '../../components/FactorList.jsx';
import LoadError from '../../components/LoadError.jsx';
import Page from '../../components/Page.jsx';
import ArtDecision from '../../components/art/ArtDecision.jsx';
import { getApplication } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { decisionHeadline, decisionLead } from '../../lib/decision.js';

export default function DecisionExplain() {
  const { id } = useParams();
  const { data: app, error } = useLoad(() => getApplication(id), [id]);

  if (error) return <LoadError error={error} backTo="/applications" backLabel="К моим заявкам" />;
  if (!app) return <Page title="Почему такое решение" subtitle="Загружаем решение…" />;

  const d = app.decision;
  const hero = {
    eyebrow: `Заявка № ${app.id} · ${app.company.name}`,
    title: 'Почему такое решение',
    art: <ArtDecision />,
  };

  if (!d) {
    return (
      <Page {...hero} subtitle="Решения пока нет — заявка на проверке.">
        <Card className="stack">
          <p className="m0">Как только банк примет решение, здесь появятся факторы и объяснение.</p>
          <div className="row"><Button to={`/applications/${app.id}`} variant="secondary">К статусу заявки</Button></div>
        </Card>
      </Page>
    );
  }

  return (
    <Page {...hero} subtitle={decisionHeadline(d)} extra={<StatusBadge status={d.outcome} />}>
      <div className="columns">
        <div className="stack">
          {/* Решение банка — нейтральные панели; объяснение ИИ — отдельно, фиолетовым */}
          <Card className="stack">
            <h2>Что повлияло на решение</h2>
            <p className="muted m0">{decisionLead(d.outcome)}</p>
            {d.commentForClient && <p className="m0 raised"><b>Комментарий банка:</b> {d.commentForClient}</p>}
            <FactorList factors={app.factors ?? []} />
            <FactorLegend />
          </Card>

          <div className="row">
            {app.offer && <Button to={`/applications/${app.id}/offer`}>Посмотреть предложение</Button>}
            <Button to={`/applications/${app.id}`} variant="secondary">К статусу заявки</Button>
          </div>
        </div>

        <aside className="stack">
          {app.explanation && (
            <>
              <AiHint label="Объяснение простыми словами">{app.explanation.text}</AiHint>
              <p className="muted small m0">Сформировано автоматически из тех же данных, по которым принято решение. Это пояснение, а не решение банка.</p>
            </>
          )}
          {app.improvements?.length > 0 && (
            <Card className="stack">
              <h3>Как улучшить условия</h3>
              <ol className="m0">{app.improvements.map((s) => <li key={s}>{s}</li>)}</ol>
            </Card>
          )}
        </aside>
      </div>
    </Page>
  );
}
