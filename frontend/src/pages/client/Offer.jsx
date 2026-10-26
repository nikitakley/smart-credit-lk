import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import AiHint from '../../components/AiHint.jsx';
import { StatusBadge } from '../../components/Badge.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import LoadError from '../../components/LoadError.jsx';
import Page from '../../components/Page.jsx';
import ArtOffer from '../../components/art/ArtOffer.jsx';
import { acceptOffer, declineOffer, getApplication } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { formatDate, formatMonths, formatPercent, formatRub } from '../../lib/format.js';

const COLLATERAL = { none: 'нет' };

export default function Offer() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: app, error } = useLoad(() => getApplication(id), [id]);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);

  if (error) return <LoadError error={error} backTo="/applications" backLabel="К моим заявкам" />;
  if (!app) return <Page title="Предложение банка" subtitle="Загружаем предложение…" />;

  const o = app.offer;
  if (!o) {
    return (
      <Page eyebrow={`Заявка № ${app.id}`} title="Предложение банка" subtitle="Предложения пока нет — оно появится после решения банка." art={<ArtOffer />}>
        <div className="row"><Button to={`/applications/${app.id}`} variant="secondary">К статусу заявки</Button></div>
      </Page>
    );
  }

  const responded = ['signing', 'issued', 'declined_by_client'].includes(app.status);
  const expired = Date.parse(o.validUntil) < Date.now();
  const respond = async (fn, to) => {
    setBusy(true);
    setActionError(null);
    try {
      await fn(app.id);
      navigate(to);
    } catch (err) {
      setActionError(err.message); // например, offer_expired — срок предложения истёк
      setBusy(false);
    }
  };
  const rb = o.rateBreakdown;

  // Заголовок hero — сама сумма, под ней фундамент
  return (
    <Page
      eyebrow={`Предложение по заявке № ${app.id}`}
      title={<span className="fundament">{formatRub(o.amount)}</span>}
      subtitle={`на ${formatMonths(o.termMonths)} под ${formatPercent(o.rate)} годовых — платёж ≈ ${formatRub(o.monthlyPayment)} в месяц`}
      extra={(
        <div className="row">
          <StatusBadge status={responded ? app.status : o.type} />
          <span className="small">Действует до {formatDate(o.validUntil)}</span>
        </div>
      )}
      art={<ArtOffer />}
    >
      <div className="columns">
        <Card className="stack">
          <h2>Условия</h2>
          <div className="terms">
            <div className="term"><div className="muted term__label">Ставка, годовых</div><div className="term__value">{formatPercent(o.rate)}</div></div>
            <div className="term"><div className="muted term__label">Срок</div><div className="term__value">{formatMonths(o.termMonths)}</div></div>
            <div className="term"><div className="muted term__label">Ежемесячный платёж</div><div className="term__value">≈ {formatRub(o.monthlyPayment)}</div></div>
          </div>
          {rb && (
            <p className="muted small m0">
              Ставка {formatPercent(rb.rate)} = ключевая ставка ЦБ {formatPercent(rb.keyRate)} + {formatPercent(rb.productSpread)} за продукт
              {rb.riskPremium > 0 ? ` + ${formatPercent(rb.riskPremium)} за риск по оценке заявки` : ' — без надбавки за риск'}.
            </p>
          )}

          {o.type === 'counter_offer' && (
            <>
              <h3>Что изменилось относительно заявки</h3>
              <table className="table table--body">
                <thead><tr><th></th><th>В заявке</th><th>Предложение</th></tr></thead>
                <tbody>
                  <tr><td className="muted">Сумма</td><td>{formatRub(o.requested.amount)}</td><td><b>{formatRub(o.amount)}</b></td></tr>
                  <tr><td className="muted">Срок</td><td>{o.requested.termMonths} мес.</td><td>{o.termMonths} мес.</td></tr>
                  <tr><td className="muted">Залог</td><td>{COLLATERAL[o.requested.collateral]}</td><td>{o.collateralRequired === 'none' ? 'не требуется' : 'требуется'}</td></tr>
                </tbody>
              </table>
            </>
          )}

          {responded ? (
            <div className="row">
              <StatusBadge status={app.status} />
              {app.status === 'signing'
                ? <Button to={`/applications/${app.id}/sign`}>Подписать договор</Button>
                : <Button to={`/applications/${app.id}`} variant="secondary">К статусу заявки</Button>}
            </div>
          ) : (
            <div className="row">
              <Button variant="accent" disabled={busy || expired} onClick={() => respond(acceptOffer, `/applications/${app.id}/sign`)}>Принять предложение</Button>
              <Button variant="secondary" to={`/applications/${app.id}/decision`}>Почему такие условия</Button>
              <Button variant="secondary" disabled={busy} onClick={() => respond(declineOffer, `/applications/${app.id}`)}>Отказаться</Button>
            </div>
          )}
          {expired && !responded && <p className="muted small m0">Срок действия предложения истёк.</p>}
          {actionError && <p className="m0 caveat"><span aria-hidden="true">! </span>{actionError}</p>}
        </Card>

        <aside className="stack">
          <AiHint>
            Платёж ≈ {formatRub(o.monthlyPayment)} в месяц.{' '}
            {o.type === 'counter_offer'
              ? 'Если нужна полная сумма, её можно запросить повторно с залогом.'
              : 'Проверьте, что он укладывается в ваш ежемесячный бюджет.'}
          </AiHint>
          <Card className="stack">
            <h3>Что дальше</h3>
            <ol className="m0">
              <li>Примите предложение — банк сформирует договор</li>
              <li>Подпишите договор кодом здесь же, в кабинете</li>
              <li>Деньги поступят на расчётный счёт сразу после подписи</li>
            </ol>
          </Card>
          <p className="muted small m0">Данные синтетические. Платёж: аннуитет.</p>
        </aside>
      </div>
    </Page>
  );
}
