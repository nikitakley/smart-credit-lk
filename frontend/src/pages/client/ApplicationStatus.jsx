import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { StatusBadge } from '../../components/Badge.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import ChecksList from '../../components/ChecksList.jsx';
import Field from '../../components/Field.jsx';
import LoadError from '../../components/LoadError.jsx';
import Page from '../../components/Page.jsx';
import StatusTimeline from '../../components/StatusTimeline.jsx';
import RingGauge from '../../components/art/RingGauge.jsx';
import { fieldErrors, getApplication, respondInfo } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { IN_PROGRESS, buildTimeline } from '../../config/statuses.js';
import { decisionHeadline } from '../../lib/decision.js';
import { formatDateTime, formatRub } from '../../lib/format.js';

// Ответ на запрос дополнительной информации (статус docs_requested)
function InfoRequestForm({ app }) {
  const req = app.infoRequest;
  const [answers, setAnswers] = useState(Object.fromEntries(req.items.map((i) => [i.code, ''])));
  const [comment, setComment] = useState('');
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [busy, setBusy] = useState(false);

  const send = async () => {
    const local = Object.fromEntries(req.items
      .filter((i) => i.required !== false && !answers[i.code].trim())
      .map((i) => [`answers.${i.code}`, 'Обязательное поле']));
    setErrors(local);
    if (Object.keys(local).length) return;
    setBusy(true);
    setFormError(null);
    try {
      await respondInfo(app.id, req.items.map((i) => ({ code: i.code, value: answers[i.code].trim() })), comment.trim());
    } catch (err) {
      setErrors(fieldErrors(err));
      setFormError(err.fields?.length ? null : err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h3>Банку нужна информация</h3>
      {req.comment && <p className="m0 raised"><b>Комментарий банка:</b> {req.comment}</p>}
      {formError && <p className="m0 caveat">{formError}</p>}
      {req.items.map((i) => (
        <Field
          key={i.code}
          label={i.label}
          inputMode={i.type === 'number' ? 'numeric' : undefined}
          value={answers[i.code]}
          onChange={(e) => setAnswers({ ...answers, [i.code]: i.type === 'number' ? e.target.value.replace(/\D/g, '') : e.target.value })}
          error={errors[`answers.${i.code}`]}
        />
      ))}
      <Field label="Комментарий (необязательно)" value={comment} onChange={(e) => setComment(e.target.value)} />
      <Button disabled={busy} onClick={send}>Отправить ответ</Button>
    </>
  );
}

export default function ApplicationStatus() {
  const { id } = useParams();
  // Опрос раз в 10 секунд — клиент видит решение аналитика без перезагрузки
  const { data: app, error } = useLoad(() => getApplication(id), [id], { pollMs: 10000 });

  if (error) return <LoadError error={error} backTo="/applications" backLabel="К моим заявкам" />;
  if (!app) return <Page title={`Заявка № ${id}`} subtitle="Загружаем заявку…" />;

  const history = app.history ?? [];
  const steps = buildTimeline(history);
  const passed = steps.filter((s) => s.state !== 'upcoming').length;
  const draft = app.status === 'draft';
  const infoOpen = app.status === 'docs_requested' && app.infoRequest && !app.infoRequest.respondedAt;

  let side;
  if (draft) {
    side = (
      <>
        <h3>Черновик</h3>
        <p className="m0">Заявка ещё не отправлена в банк.</p>
        <Button to={`/apply?draft=${app.id}`}>Продолжить заполнение</Button>
      </>
    );
  } else if (app.issuance) {
    side = (
      <>
        <h3>Кредит выдан</h3>
        <div className="display-sm"><span className="fundament">{formatRub(app.issuance.amount)}</span></div>
        <dl className="kv-grid kv-grid--1">
          <div><dt>Договор</dt><dd>{app.issuance.contractNumber}, подписан {formatDateTime(app.issuance.signedAt)}</dd></div>
          <div><dt>Зачислено</dt><dd>На расчётный счёт •••• {app.issuance.account.slice(-4)}</dd></div>
        </dl>
        <p className="muted small m0">Выдача смоделирована: реальных проводок нет.</p>
      </>
    );
  } else if (app.status === 'signing') {
    side = (
      <>
        <h3>Осталось подписать договор</h3>
        <p className="m0">{app.decision ? `${decisionHeadline(app.decision)}. ` : ''}Договор {app.signing?.contractNumber} готов.</p>
        <Button to={`/applications/${app.id}/sign`}>Подписать договор</Button>
      </>
    );
  } else if (infoOpen) {
    side = <InfoRequestForm key={app.infoRequest.requestedAt} app={app} />;
  } else if (app.decision) {
    side = (
      <>
        <h3>Решение</h3>
        <p className="m0">{decisionHeadline(app.decision)}</p>
        <Button to={`/applications/${app.id}/decision`} variant="secondary">Почему такое решение</Button>
        {app.offer && <Button to={`/applications/${app.id}/offer`}>Предложение банка</Button>}
      </>
    );
  } else {
    side = (
      <>
        <h3>Решение</h3>
        <p className="muted small m0">
          {app.status === 'manual_review' ? 'Заявку проверяет специалист банка.' : 'Появится после проверки.'}
          {IN_PROGRESS.includes(app.status) || app.status === 'manual_review' ? ' Страница обновится сама.' : ''}
        </p>
      </>
    );
  }

  return (
    <Page
      title={`Заявка № ${app.id}`}
      subtitle={`${app.company.name} · ${app.productName ?? 'продукт не выбран'} · запрошено ${formatRub(app.amount)}${app.termMonths ? ` на ${app.termMonths} мес.` : ''}`}
      extra={<StatusBadge status={app.status} />}
      art={draft ? null : (
        <RingGauge
          ratio={steps.length ? passed / steps.length : 0}
          value={`${passed}/${steps.length}`}
          caption="этапов пройдено"
          tone={app.status === 'issued' ? 'aqua' : 'red'}
        />
      )}
    >
      <div className="grid-2">
        <div className="stack">
          {!draft && (
            <Card>
              <h2 className="section-title">Статус</h2>
              <StatusTimeline steps={steps} />
            </Card>
          )}
          {app.checks?.length > 0 && (
            <Card className="stack">
              <h2>Проверки банка</h2>
              <ChecksList checks={app.checks} />
            </Card>
          )}
        </div>
        <Card className="stack">{side}</Card>
      </div>
    </Page>
  );
}
