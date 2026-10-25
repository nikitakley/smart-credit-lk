import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import AiHint from '../../components/AiHint.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import Field from '../../components/Field.jsx';
import Page from '../../components/Page.jsx';
import ArtDocument from '../../components/art/ArtDocument.jsx';
import { getApplication, requestSignCode, signContract } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { formatMonths, formatPercent, formatRub } from '../../lib/format.js';

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

  if (error) return <Page title="Заявка не найдена" subtitle={`Проверьте номер: ${id}`} />;
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

  const getCode = async () => {
    setBusy(true);
    setSent(await requestSignCode(app.id));
    setCode('');
    setCodeError(null);
    setBusy(false);
  };

  const sign = async () => {
    setBusy(true);
    try {
      await signContract(app.id, code);
      navigate(`/applications/${app.id}`);
    } catch {
      setCodeError('Код не подходит — проверьте цифры или запросите новый');
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
            <div className="row"><Button disabled={!agree || busy} onClick={getCode}>Получить код для подписи</Button></div>
          ) : (
            <>
              <p className="raised m0">
                Демо: в рабочей версии код придёт в SMS на {app.contact.phone}. Ваш код — <b className="code">{sent.code}</b>
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
