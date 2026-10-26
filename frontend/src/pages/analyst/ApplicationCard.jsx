import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import AiHint from '../../components/AiHint.jsx';
import { StatusBadge } from '../../components/Badge.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import ChecksList from '../../components/ChecksList.jsx';
import FactorList from '../../components/FactorList.jsx';
import Field from '../../components/Field.jsx';
import LoadError from '../../components/LoadError.jsx';
import Page from '../../components/Page.jsx';
import RingGauge from '../../components/art/RingGauge.jsx';
import { decide, fieldErrors, getAnalystApplication, getDictionaries, refreshChecks } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { ACTORS, ANALYST_DECIDES, CHECKS_REFRESH, STATUS } from '../../config/statuses.js';
import { decisionHeadline } from '../../lib/decision.js';
import { formatAge, formatDate, formatDateTime, formatPercent, formatRub } from '../../lib/format.js';

const ACTIONS = [
  { key: 'approve', label: 'Одобрить' },
  { key: 'counter_offer', label: 'Контрпредложение' },
  { key: 'request_docs', label: 'Запросить информацию' },
  { key: 'reject', label: 'Отказать' },
];

// Форма решения специалиста. Доступна в статусах manual_review и docs_requested (ANALYST_DECIDES)
function DecisionForm({ app, dicts }) {
  const rec = app.systemRecommendation;
  const [action, setAction] = useState(null);
  const [amount, setAmount] = useState(rec?.amount && rec.amount < app.amount ? String(rec.amount) : '');
  const [comment, setComment] = useState('');
  const [reasonCode, setReasonCode] = useState(null);
  const [infoCodes, setInfoCodes] = useState([]);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [busy, setBusy] = useState(false);

  const toggleInfo = (code) => setInfoCodes(infoCodes.includes(code) ? infoCodes.filter((c) => c !== code) : [...infoCodes, code]);

  const submit = async () => {
    // Те же правила, что на бэке, — чтобы не гонять запрос с заведомо пустыми полями
    const next = {};
    const counterAmount = Number(amount);
    if (action === 'counter_offer' && !(counterAmount > 0 && counterAmount < app.amount)) {
      next.amount = `Сумма должна быть меньше запрошенной (${formatRub(app.amount)})`;
    }
    if (action === 'reject' && !reasonCode) next.reasonCode = 'Выберите причину отказа';
    if (action === 'request_docs' && !infoCodes.length) next.infoItems = 'Отметьте, что запросить у клиента';
    if (action !== 'approve' && !comment.trim()) next.commentForClient = 'Нужен комментарий для клиента';
    setErrors(next);
    if (Object.keys(next).length) return;

    setBusy(true);
    setFormError(null);
    try {
      await decide(app.id, {
        action,
        amount: action === 'counter_offer' ? counterAmount : undefined,
        commentForClient: comment.trim() || undefined,
        reasonCode: action === 'reject' ? reasonCode : undefined,
        infoItems: action === 'request_docs' ? dicts.infoItems.filter((i) => infoCodes.includes(i.code)) : undefined,
      });
      setAction(null);
      setComment('');
      setInfoCodes([]);
      setReasonCode(null);
    } catch (err) {
      setErrors(fieldErrors(err));
      setFormError(err.fields?.length ? null : err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="chips" role="group" aria-label="Действие">
        {ACTIONS.map((a) => (
          <button key={a.key} type="button" className="chip" aria-pressed={action === a.key} onClick={() => { setAction(a.key); setErrors({}); }}>
            {a.label}
          </button>
        ))}
      </div>

      {action === 'approve' && <p className="m0">Одобрить запрошенные {formatRub(app.amount)} на {app.termMonths} мес.</p>}

      {action === 'counter_offer' && (
        <Field
          label="Сумма контрпредложения, ₽"
          inputMode="numeric"
          value={amount}
          onChange={(e) => setAmount(e.target.value.replace(/\D/g, ''))}
          hint={rec?.amount ? `Система рекомендует ${formatRub(rec.amount)}` : `Меньше запрошенной — ${formatRub(app.amount)}`}
          error={errors.amount}
        />
      )}

      {action === 'reject' && (
        <fieldset className="stack-sm">
          <legend className="small muted">Причина отказа</legend>
          <div className="chips">
            {dicts.rejectReasons.map((r) => (
              <button key={r.code} type="button" className="chip" aria-pressed={reasonCode === r.code} onClick={() => setReasonCode(r.code)}>
                {r.label}
              </button>
            ))}
          </div>
          {errors.reasonCode && <p className="m0 caveat">{errors.reasonCode}</p>}
        </fieldset>
      )}

      {action === 'request_docs' && (
        <fieldset className="stack-sm">
          <legend className="small muted">Что запросить у клиента</legend>
          {dicts.infoItems.map((i) => (
            <label key={i.code} className="check">
              <input type="checkbox" checked={infoCodes.includes(i.code)} onChange={() => toggleInfo(i.code)} />
              <span>{i.label}</span>
            </label>
          ))}
          {errors.infoItems && <p className="m0 caveat">{errors.infoItems}</p>}
        </fieldset>
      )}

      {action && action !== 'approve' && (
        <Field
          label="Комментарий для клиента"
          placeholder="Увидит клиент"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          hint="Покажем клиенту на странице заявки"
          error={errors.commentForClient}
        />
      )}

      {formError && <p className="m0 caveat">{formError}</p>}
      {action && (
        <Button variant={action === 'approve' ? 'accent' : 'primary'} disabled={busy} onClick={submit}>
          {action === 'approve' ? `Одобрить ${formatRub(app.amount)}` : 'Отправить решение'}
        </Button>
      )}
    </>
  );
}

// Проверки по источникам и повторный запрос данных. Запрос идёт 1–1,5 с, при зависшем источнике — до ~10 с
function ChecksCard({ app, dicts, onRefreshed }) {
  const [busy, setBusy] = useState(false);
  const [refreshError, setRefreshError] = useState(null);
  const canRefresh = CHECKS_REFRESH.includes(app.status);
  if (!app.checks?.length && !canRefresh) return null;

  const refresh = async () => {
    setBusy(true);
    setRefreshError(null);
    try {
      onRefreshed(await refreshChecks(app.id));
    } catch (err) {
      setRefreshError(err.message); // 409 — карточка перечитается сама
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="stack">
      <div className="toolbar">
        <h2>Проверки</h2>
        {canRefresh && (
          <Button variant="secondary" size="s" disabled={busy} aria-busy={busy} onClick={refresh}>
            {busy ? 'Запрашиваем источники…' : 'Обновить данные из источников'}
          </Button>
        )}
      </div>
      {busy && <p className="muted small m0" role="status">Запрашиваем ЕГРЮЛ, НБКИ и «Прозрачный бизнес». Если источник не отвечает, это может занять до 10 секунд.</p>}
      {refreshError && <p className="m0 caveat">{refreshError}</p>}
      {app.checks?.length > 0
        ? <ChecksList checks={app.checks} withDetails unavailableReasons={dicts?.unavailableReasons} />
        : <p className="muted m0">Данные из источников ещё не запрашивались.</p>}
    </Card>
  );
}

export default function ApplicationCard() {
  const { id } = useParams();
  const { data: app, error, mutate } = useLoad(() => getAnalystApplication(id), [id], { pollMs: 15000 });
  const { data: dicts } = useLoad(getDictionaries, []);

  const back = <Link to="/analyst" className="hero__back">← Очередь заявок</Link>;
  if (error) return <LoadError error={error} eyebrow={back} backTo="/analyst" backLabel="К очереди заявок" />;
  if (!app) return <Page eyebrow={back} title={`Заявка № ${id}`} subtitle="Загружаем заявку…" />;

  const c = app.company;
  const rec = app.systemRecommendation;
  const inputs = app.scoringInputs;
  const rb = app.rateBreakdown;
  const score = app.score;
  const canDecide = ANALYST_DECIDES.includes(app.status);

  return (
    <Page
      eyebrow={back}
      title={`Заявка № ${app.id}`}
      subtitle={[c.name, `ИНН ${c.inn}`, app.productName, app.amount != null && `${formatRub(app.amount)}${app.termMonths ? ` на ${app.termMonths} мес.` : ''}`].filter(Boolean).join(' · ')}
      extra={<StatusBadge status={app.status} />}
      art={score ? <RingGauge ratio={score.value / (score.max ?? 100)} value={score.value} caption={`из ${score.max ?? 100} · оценка скоринга`} /> : null}
    >
      <div className="columns">
        <div className="stack">
          <Card className="stack">
            <h2>Компания</h2>
            <dl className="kv-grid">
              <div><dt>{c.type === 'ip' ? 'ОГРНИП' : 'ОГРН'}</dt><dd>{c.ogrn}</dd></div>
              <div><dt>Дата регистрации</dt><dd>{formatDate(c.registeredAt)}</dd></div>
              <div><dt>{c.directorTitle ?? (c.type === 'ip' ? 'Предприниматель' : 'Руководитель')}</dt><dd>{c.director}</dd></div>
              <div><dt>ОКВЭД</dt><dd>{c.okved.code} — {c.okved.title}</dd></div>
              <div><dt>Юридический адрес</dt><dd>{c.legalAddress}</dd></div>
              {c.founders?.length > 0 && (
                <div><dt>Учредители</dt><dd>{c.founders.map((f) => `${f.name}${f.sharePercent != null ? ` (${f.sharePercent}%)` : ''}`).join(', ')}</dd></div>
              )}
              <div><dt>Источник</dt><dd>{c.source ?? 'ЕГРЮЛ'}, {formatDate(c.fetchedAt)}</dd></div>
            </dl>
          </Card>

          <ChecksCard app={app} dicts={dicts} onRefreshed={mutate} />

          <Card className="stack">
            <div className="toolbar">
              <h2>Скоринг</h2>
              {score && <span className="score">Оценка: {score.value} из {score.max ?? 100} · порог {score.minScore}</span>}
            </div>
            {inputs ? (
              // Входные данные — чтобы было видно, из чего получилась рекомендация
              <dl className="kv-grid">
                <div><dt>Выручка в месяц</dt><dd>{formatRub(inputs.monthlyRevenue)}</dd></div>
                <div><dt>Динамика за 12 мес.</dt><dd>{inputs.revenueGrowth > 0 ? '+' : ''}{inputs.revenueGrowth}%</dd></div>
                <div><dt>Платежи по кредитам</dt><dd>{formatRub(inputs.loanPayments)} · {inputs.dtiNow}% выручки</dd></div>
                <div><dt>Нагрузка с новым кредитом</dt><dd>{inputs.dtiWithRequested}% выручки</dd></div>
                <div><dt>Просрочки за 2 года</dt><dd>{inputs.overdues24m}</dd></div>
                <div><dt>Срок работы</dt><dd>{formatAge(inputs.ageMonths)}</dd></div>
                <div><dt>Можно выдать до</dt><dd>{formatRub(inputs.affordable)}</dd></div>
              </dl>
            ) : (
              <p className="muted m0">Скоринг ещё не проводился — данные появятся после автоматической проверки.</p>
            )}
            {rb && (
              <p className="muted small m0">
                Ставка {formatPercent(rb.rate)} = ключевая {formatPercent(rb.keyRate)} + {formatPercent(rb.productSpread)} за продукт + {formatPercent(rb.riskPremium)} за риск.
              </p>
            )}
            {app.factors?.length > 0 && <FactorList factors={app.factors} />}
          </Card>

          <Card className="stack">
            <h2>История</h2>
            <ul className="events">
              {app.history.map((h, i) => (
                <li key={i}>
                  <span className="muted small">{formatDateTime(h.at)}</span>
                  <span>{STATUS[h.status]?.label ?? h.status} · {ACTORS[h.actor] ?? h.actor}{h.note && <span className="muted"> — {h.note}</span>}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <aside className="stack">
          {rec ? (
            <>
              <AiHint label="Рекомендация системы">{rec.text}</AiHint>
              <p className="muted small m0">Рассчитана по правилам скоринга. Окончательное решение принимает специалист.</p>
            </>
          ) : (
            <p className="muted small m0">Рекомендация системы появится после скоринга.</p>
          )}

          {app.infoRequest && (
            <Card className="stack">
              <h3>Запрос информации</h3>
              {app.infoRequest.comment && <p className="m0">{app.infoRequest.comment}</p>}
              <ul className="m0">{app.infoRequest.items.map((i) => <li key={i.code}>{i.label}</li>)}</ul>
              <p className="muted small m0">
                Запрошено {formatDateTime(app.infoRequest.requestedAt)}
                {app.infoRequest.respondedAt ? ` · клиент ответил ${formatDateTime(app.infoRequest.respondedAt)}` : ' · ждём ответа клиента'}
              </p>
            </Card>
          )}

          <Card className="stack">
            <h3>Решение</h3>
            {canDecide && dicts ? (
              <DecisionForm key={app.updatedAt} app={app} dicts={dicts} />
            ) : canDecide ? (
              <p className="muted small m0">Загружаем справочники…</p>
            ) : app.decision ? (
              <>
                <div><StatusBadge status={app.decision.outcome} /></div>
                <p className="m0">{decisionHeadline(app.decision)}</p>
                {app.decision.commentForClient && <p className="muted small m0">Клиенту: {app.decision.commentForClient}</p>}
                <p className="muted small m0">
                  {app.decision.decidedBy === 'system'
                    ? 'Решение принято автоматически'
                    : app.decision.followedSystem ? 'Совпадает с рекомендацией системы' : 'Отличается от рекомендации системы'}
                </p>
              </>
            ) : (
              <p className="muted small m0">Решение принимается после автоматической проверки — в статусе «На проверке у специалиста».</p>
            )}
          </Card>
        </aside>
      </div>
    </Page>
  );
}
