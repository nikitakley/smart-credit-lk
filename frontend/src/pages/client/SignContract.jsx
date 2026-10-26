import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import AiHint from '../../components/AiHint.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import Field from '../../components/Field.jsx';
import LoadError from '../../components/LoadError.jsx';
import Page from '../../components/Page.jsx';
import ArtDocument from '../../components/art/ArtDocument.jsx';
import { getApplication, requestSignCode, signContract } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { formatMonths, formatPercent, formatRub } from '../../lib/format.js';

const formatTime = (iso) => new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });

// Подписание договора простой ЭП с кодом подтверждения и моделируемая выдача.
// Смоделировано внутри продукта (FAQ п. 12): без SMS и без интеграции с ДБО / Госключом.
export default function SignContract() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: app, error } = useLoad(() => getApplication(id), [id]);
  const [agree, setAgree] = useState(false);
  const [sent, setSent] = useState(null);
  const [code, setCode] = useState('');
  const [codeError, setCodeError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (error) return <LoadError error={error} backTo="/applications" backLabel="К моим заявкам" />;
  if (!app) return <Page title="Подписание договора" subtitle="Загружаем договор…" />;

  if (app.status !== 'signing') {
    return (
      <Page eyebrow={`Заявка № ${app.id}`} title="Подписание договора" subtitle={app.status === 'issued' ? 'Договор уже подписан, кредит выдан.' : 'Договор появится после того, как вы примете предложение банка.'}>
        <div className="row"><Button to={`/applications/${app.id}`} variant="secondary">К статусу заявки</Button></div>
      </Page>
    );
  }

  const o = app.offer;
  const s = app.signing;

  const phone = app.contact?.phone ?? app.company.phone;

  const getCode = async () => {
    setBusy(true);
    setCode('');
    setCodeError(null);
    try {
      setSent(await requestSignCode(app.id));
    } catch (err) {
      setCodeError(err.message);
    } finally {
      setBusy(false);
    }
  };

  // Код истёк или попытки кончились — нужен новый код
  const NEED_NEW_CODE = ['code_expired', 'code_attempts_exceeded', 'code_not_requested'];

  const sign = async () => {
    setBusy(true);
    try {
      await signContract(app.id, code);
      navigate(`/applications/${app.id}`);
    } catch (err) {
      setCodeError(err.message); // текст с бэка, например «Код не подходит. Осталось попыток: 2»
      if (NEED_NEW_CODE.includes(err.code)) setSent(null);
      else if (err.code === 'invalid_code') setSent({ ...sent, attemptsLeft: Math.max(0, sent.attemptsLeft - 1) });
      setBusy(false);
    }
  };

  return (
    <Page
      eyebrow={`Договор ${s.contractNumber}`}
      title="Подписание договора"
      subtitle={`${formatRub(o.amount)} на ${formatMonths(o.termMonths)} под ${formatPercent(o.rate)} годовых. Подпишите кодом — и деньги поступят на расчётный счёт.`}
      art={<ArtDocument />}
    >
      <div className="columns">
        <Card className="stack">
          <h2>Кредитный договор</h2>
          <dl className="kv-grid">
            <div><dt>Номер</dt><dd>{s.contractNumber}</dd></div>
            <div><dt>Заёмщик</dt><dd>{app.company.name}</dd></div>
            <div><dt>Продукт</dt><dd>{app.productName}</dd></div>
            <div><dt>Сумма</dt><dd>{formatRub(o.amount)}</dd></div>
            <div><dt>Срок и ставка</dt><dd>{formatMonths(o.termMonths)}, {formatPercent(o.rate)}</dd></div>
            <div><dt>Платёж</dt><dd>≈ {formatRub(o.monthlyPayment)} в месяц</dd></div>
            <div><dt>Зачисление</dt><dd>Расчётный счёт •••• {app.company.account.slice(-4)}</dd></div>
          </dl>

          <label className="check">
            <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
            <span>Ознакомился с условиями договора и графиком платежей</span>
          </label>

          {!sent ? (
            <>
              {codeError && <p className="m0 caveat"><span aria-hidden="true">! </span>{codeError}</p>}
              <div className="row"><Button disabled={!agree || busy} onClick={getCode}>Получить код для подписи</Button></div>
            </>
          ) : (
            <>
              <p className="raised m0">
                {sent.code
                  ? <>Демо: в рабочей версии код придёт в SMS на {phone}. Ваш код — <b className="code">{sent.code}</b></>
                  : <>Код отправлен на {phone}.</>}
                <br />
                <span className="small muted">Действует до {formatTime(sent.expiresAt)} · попыток: {sent.attemptsLeft}</span>
              </p>
              <div className="inn-row">
                <Field
                  label="Код подтверждения"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={code}
                  onChange={(e) => { setCode(e.target.value.replace(/\D/g, '').slice(0, 6)); setCodeError(null); }}
                  error={codeError}
                />
                <Button variant="secondary" disabled={busy} onClick={getCode}>Новый код</Button>
              </div>
              <div className="row">
                <Button variant="accent" disabled={!agree || code.length !== 6 || busy} onClick={sign}>Подписать и получить деньги</Button>
              </div>
            </>
          )}
        </Card>

        <aside className="stack">
          <AiHint>Код подтверждает простую электронную подпись — так же, как в интернет-банке. После подписи кредит выдаётся на счёт сразу.</AiHint>
          <Card className="stack">
            <h3>Как это работает</h3>
            <ol className="m0">
              <li>Банк сформировал договор по принятому предложению</li>
              <li>Вы подтверждаете подпись кодом</li>
              <li>Деньги зачисляются на расчётный счёт компании</li>
            </ol>
          </Card>
          <p className="muted small m0">Подписание и выдача смоделированы: в рабочей версии — код из SMS или push и подпись через ДБО либо Госключ.</p>
        </aside>
      </div>
    </Page>
  );
}
