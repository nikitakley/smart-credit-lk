import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import AiHint from '../../components/AiHint.jsx';
import { StatusBadge } from '../../components/Badge.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import FactorList from '../../components/FactorList.jsx';
import Field from '../../components/Field.jsx';
import Page from '../../components/Page.jsx';
import RingGauge from '../../components/art/RingGauge.jsx';
import { decide, getApplication } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { ACTORS, STATUS } from '../../config/statuses.js';
import { decisionHeadline } from '../../lib/decision.js';
import { formatDate, formatDateTime, formatPercent, formatRub } from '../../lib/format.js';
import { DTI_LIMIT, formatAge } from '../../api/scoring.js';

// Решение можно принять, пока заявка на проверке или ждёт документы
const OPEN = ['submitted', 'scoring', 'docs_requested'];

export default function ApplicationCard() {
  const { id } = useParams();
  const { data: app, error } = useLoad(() => getApplication(id), [id]);
  const [amount, setAmount] = useState(null); // null — берём рекомендацию ИИ
  const [comment, setComment] = useState('');
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);

  const back = <Link to="/analyst" className="hero__back">← Очередь заявок</Link>;
  if (error) return <Page eyebrow={back} title="Заявка не найдена" subtitle={`Проверьте номер: ${id}`} />;
  if (!app) return <Page eyebrow={back} title={`Заявка № ${id}`} subtitle="Загружаем заявку…" />;

  const c = app.company;
  const rec = app.aiRecommendation;
  const amountValue = amount ?? (rec.amount ? String(rec.amount) : '');
  const inputs = app.scoringInputs;
  const rb = app.rateBreakdown;

  const act = async (action) => {
    const next = {};
    const counterAmount = Number(amountValue);
    if (action === 'counter_offer' && !(counterAmount > 0 && counterAmount < app.amount)) {
      next.amount = `Сумма должна быть меньше запрошенной (${formatRub(app.amount)})`;
    }
    if (action !== 'approve' && !comment.trim()) next.comment = 'Нужен комментарий для клиента';
    setErrors(next);
    if (Object.keys(next).length) return;

    setBusy(true);
    await decide(app.id, {
      action,
      amount: action === 'approve' ? app.amount : counterAmount,
      termMonths: rec.termMonths,
      rate: rec.rate,
      commentForClient: comment.trim(),
      reasonCode: action === 'reject' ? 'debt_load' : undefined,
    });
    setBusy(false);
    setComment('');
    setAmount(null);
  };

  return (
    <Page
      eyebrow={back}
      title={`Заявка № ${app.id}`}
      subtitle={`${c.name} · ИНН ${c.inn} · ${app.productName} · ${formatRub(app.amount)} на ${app.termMonths} мес.`}
      extra={<StatusBadge status={app.status} />}
      art={<RingGauge ratio={app.score.value / app.score.max} value={app.score.value} caption={`из ${app.score.max} · оценка скоринга`} />}
    >
      <div className="columns">
        <div className="stack">
          <Card className="stack">
            <h2>Компания</h2>
            <dl className="kv-grid">
              <div><dt>{c.type === 'ip' ? 'ОГРНИП' : 'ОГРН'}</dt><dd>{c.ogrn}</dd></div>
              <div><dt>Дата регистрации</dt><dd>{formatDate(c.registeredAt)}</dd></div>
              <div><dt>{c.type === 'ip' ? 'Предприниматель' : 'Руководитель'}</dt><dd>{c.director}</dd></div>
              <div><dt>ОКВЭД</dt><dd>{c.okved.code} — {c.okved.title}</dd></div>
              <div><dt>Юридический адрес</dt><dd>{c.legalAddress}</dd></div>
              <div><dt>Источник</dt><dd>{c.source}, {formatDate(c.fetchedAt)}</dd></div>
            </dl>
          </Card>

          <Card className="stack">
            <div className="toolbar">
              <h2>Скоринг</h2>
              <span className="score">Оценка: {app.score.value} из {app.score.max} · порог {app.score.minScore}</span>
            </div>
            {/* Входные данные — чтобы было видно, из чего получилась рекомендация */}
            <dl className="kv-grid">
              <div><dt>Выручка в месяц</dt><dd>{formatRub(inputs.monthlyRevenue)}</dd></div>
              <div><dt>Динамика за 12 мес.</dt><dd>{inputs.revenueGrowth > 0 ? '+' : ''}{inputs.revenueGrowth}%</dd></div>
              <div><dt>Платежи по кредитам</dt><dd>{formatRub(inputs.loanPayments)} · {inputs.dtiNow}% выручки</dd></div>
              <div><dt>Просрочки за 2 года</dt><dd>{inputs.overdues24m}</dd></div>
              <div><dt>Срок работы</dt><dd>{formatAge(inputs.ageMonths)}</dd></div>
              <div><dt>Можно выдать до</dt><dd>{formatRub(inputs.affordable)}</dd></div>
            </dl>
            <p className="muted small m0">
              Источник — синтетическая выписка за 12 месяцев. Лимит нагрузки — {Math.round(DTI_LIMIT * 100)}% выручки.
              Ставка {formatPercent(rb.rate)} = ключевая {formatPercent(rb.keyRate)} + {formatPercent(rb.productSpread)} за продукт + {formatPercent(rb.riskPremium)} за риск.
            </p>
            <FactorList factors={app.factors} />
          </Card>

          <Card className="stack">
            <h2>История</h2>
            <ul className="events">
              {app.history.map((h, i) => (
                <li key={i}>
                  <span className="muted small">{formatDateTime(h.at)}</span>
                  <span>{STATUS[h.status]?.label} · {ACTORS[h.actor]}{h.note && <span className="muted"> — {h.note}</span>}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <aside className="stack">
          <AiHint label="Рекомендация системы">{rec.text}</AiHint>
          <p className="muted small m0">Рассчитана по правилам скоринга. Окончательное решение принимает аналитик.</p>

          <Card className="stack">
            <h3>Решение</h3>
            {OPEN.includes(app.status) ? (
              <>
                <Field
                  label="Сумма контрпредложения, ₽"
                  inputMode="numeric"
                  value={amountValue}
                  onChange={(e) => setAmount(e.target.value.replace(/\D/g, ''))}
                  hint={rec.amount ? `Система рекомендует ${formatRub(rec.amount)}` : 'Система рекомендует отказ'}
                  error={errors.amount}
                />
                <Field
                  label="Комментарий для клиента"
                  placeholder="Увидит клиент"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  hint="Покажем на экране «Почему такое решение»"
                  error={errors.comment}
                />
                <Button disabled={busy} onClick={() => act('approve')}>Одобрить {formatRub(app.amount)}</Button>
                <Button variant="secondary" disabled={busy} onClick={() => act('counter_offer')}>Контрпредложение</Button>
                <Button variant="secondary" disabled={busy} onClick={() => act('request_docs')}>Запросить документы</Button>
                <Button variant="secondary" disabled={busy} onClick={() => act('reject')}>Отказать</Button>
              </>
            ) : app.decision ? (
              <>
                <div><StatusBadge status={app.decision.outcome} /></div>
                <p className="m0">{decisionHeadline(app.decision)}</p>
                {app.decision.commentForClient && <p className="muted small m0">Клиенту: {app.decision.commentForClient}</p>}
                <p className="muted small m0">
                  {app.decision.followedAi ? 'Совпадает с рекомендацией системы' : 'Отличается от рекомендации системы'}
                </p>
              </>
            ) : (
              <p className="muted small m0">Решение по заявке уже принято.</p>
            )}
          </Card>
        </aside>
      </div>
    </Page>
  );
}
