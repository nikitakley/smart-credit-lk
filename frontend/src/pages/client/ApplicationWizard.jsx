import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import AiHint from '../../components/AiHint.jsx';
import Badge from '../../components/Badge.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import Field from '../../components/Field.jsx';
import Page from '../../components/Page.jsx';
import ArtDocument from '../../components/art/ArtDocument.jsx';
import { createApplication, getClientSession, getCompany, getProducts } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { annuity, formatDate, formatMonths, formatPercent, formatRub } from '../../lib/format.js';

const STEPS = ['Компания', 'Контакты', 'Условия', 'Отправка'];
const TERMS = [3, 6, 12, 18, 24, 36, 48, 60];
// Цель — enum из контракта с бэком (+ cash_gap из помощника подбора)
const PURPOSES = [
  { value: 'working_capital', label: 'Оборотные средства' },
  { value: 'cash_gap', label: 'Кассовый разрыв' },
  { value: 'equipment', label: 'Оборудование, транспорт' },
  { value: 'renovation', label: 'Ремонт, расширение' },
  { value: 'refinancing', label: 'Рефинансирование' },
];
const CONSENTS = [
  { key: 'bki', label: 'Согласие на запрос в бюро кредитных историй' },
  { key: 'personalData', label: 'Согласие на обработку персональных данных' },
];

export default function ApplicationWizard() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { data: products } = useLoad(getProducts, []);
  const { data: session } = useLoad(getClientSession, []);

  const [step, setStep] = useState(0);
  const [company, setCompany] = useState(null);
  const [lookupError, setLookupError] = useState(null);
  const [contact, setContact] = useState(null);
  const [terms, setTerms] = useState({
    productId: params.get('product') ?? 'working-capital',
    amount: params.get('amount') ?? '2000000',
    termMonths: Number(params.get('term')) || 24,
    purpose: params.get('purpose') ?? 'working_capital',
  });
  const [consents, setConsents] = useState({ bki: false, personalData: false });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  // Клиент уже авторизован: реквизиты его компании подтягиваем по ИНН сразу
  useEffect(() => {
    if (!session?.inn || company) return;
    getCompany(session.inn)
      .then((c) => { setCompany(c); setContact({ name: c.director, phone: c.phone, email: c.email }); })
      .catch(() => setLookupError('Не удалось получить данные из ЕГРЮЛ — попробуйте позже'));
  }, [session, company]);

  const product = products?.find((p) => p.id === terms.productId);
  const amount = Number(terms.amount) || 0;
  const termOptions = TERMS.filter((t) => !product || t <= product.maxTermMonths);

  // Срок из помощника может быть больше, чем позволяет продукт — прижимаем к максимуму
  useEffect(() => {
    if (product && terms.termMonths > product.maxTermMonths) setTerms((t) => ({ ...t, termMonths: product.maxTermMonths }));
  }, [product, terms.termMonths]);
  const payment = product && amount > 0 ? annuity(amount, product.rateFrom, terms.termMonths) : null;

  const validate = () => {
    const e = {};
    if (step === 1) {
      if (!contact.name.trim()) e.name = 'Укажите контактное лицо';
      if (!/^\+?[\d\s()-]{10,}$/.test(contact.phone)) e.phone = 'Телефон в формате +7 900 000-00-00';
      if (!/^\S+@\S+\.\S+$/.test(contact.email)) e.email = 'Проверьте email';
    }
    if (step === 2 && product) {
      if (amount < product.minAmount || amount > product.maxAmount) {
        e.amount = `От ${formatRub(product.minAmount)} до ${formatRub(product.maxAmount)} для этого продукта`;
      }
    }
    if (step === 3 && !(consents.bki && consents.personalData)) e.consents = 'Без согласий банк не сможет рассмотреть заявку';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const next = () => { if (validate()) setStep(step + 1); };

  const setProduct = (productId) => {
    const p = products.find((x) => x.id === productId);
    setTerms((t) => ({ ...t, productId, termMonths: Math.min(t.termMonths, p.maxTermMonths) }));
  };

  const submit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    const { id } = await createApplication({ productId: terms.productId, amount, termMonths: terms.termMonths, purpose: terms.purpose, contact });
    navigate(`/applications/${id}`);
  };

  const purposeLabel = PURPOSES.find((p) => p.value === terms.purpose)?.label;

  return (
    <Page
      title="Заявка на кредит"
      subtitle={`${product?.name ?? 'Кредит для бизнеса'} · шаг ${step + 1} из ${STEPS.length}. Реквизиты компании уже подтянули — осталось указать условия.`}
      extra={(
        <ol className="steps steps--dark">
          {STEPS.map((s, i) => (
            <li
              key={s}
              className={`steps__item ${i < step ? 'steps__item--done' : ''} ${i === step ? 'steps__item--current' : ''}`}
              aria-current={i === step ? 'step' : undefined}
            >
              {s}
            </li>
          ))}
        </ol>
      )}
      art={<ArtDocument />}
    >
      <div className="columns">
        <Card className="stack">
          {step === 0 && (
            <>
              <h2>Реквизиты компании</h2>
              {!company && !lookupError && <p className="muted m0">Получаем данные из ЕГРЮЛ по ИНН {session?.inn}…</p>}
              {lookupError && <p className="m0 caveat">{lookupError}</p>}
              {company && (
                <>
                  <div className="row">
                    <Badge tone="success">Данные получены</Badge>
                    <span className="muted small">по данным {company.source} на {formatDate(company.fetchedAt)}</span>
                  </div>
                  <div className="fields-2">
                    <Field autofilled label="ИНН" value={company.inn} />
                    <Field autofilled label="Название" value={company.name} />
                    <Field autofilled label={company.type === 'ip' ? 'ОГРНИП' : 'ОГРН'} value={company.ogrn} />
                    {company.kpp && <Field autofilled label="КПП" value={company.kpp} />}
                    <Field autofilled label="Дата регистрации" value={formatDate(company.registeredAt)} />
                    <Field autofilled label={company.type === 'ip' ? 'Предприниматель' : 'Руководитель'} value={company.director} />
                    <Field autofilled className="span-2" label="ОКВЭД" value={`${company.okved.code} — ${company.okved.title}`} />
                    <Field autofilled className="span-2" label="Юридический адрес" value={company.legalAddress} />
                  </div>
                  <p className="muted small m0">Вы вошли как клиент банка, поэтому вводить ИНН и реквизиты не нужно.</p>
                  <div className="row"><Button onClick={next}>Всё верно, дальше</Button></div>
                </>
              )}
            </>
          )}

          {step === 1 && contact && (
            <>
              <h2>Контактное лицо</h2>
              <p className="muted m0">С ним свяжется банк, если понадобятся уточнения.</p>
              <div className="fields-2">
                <Field className="span-2" label="ФИО" value={contact.name} error={errors.name} onChange={(e) => setContact({ ...contact, name: e.target.value })} />
                <Field label="Телефон" inputMode="tel" value={contact.phone} error={errors.phone} onChange={(e) => setContact({ ...contact, phone: e.target.value })} />
                <Field label="Email" inputMode="email" value={contact.email} error={errors.email} onChange={(e) => setContact({ ...contact, email: e.target.value })} />
              </div>
              <div className="row">
                <Button variant="secondary" onClick={() => setStep(0)}>Назад</Button>
                <Button onClick={next}>Далее</Button>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <h2>Условия кредита</h2>
              <div className="stack" style={{ gap: 'var(--space-3)' }}>
                <div className="muted small">Продукт</div>
                <div className="chips">
                  {(products ?? []).map((p) => (
                    <button key={p.id} type="button" className="chip" aria-pressed={terms.productId === p.id} onClick={() => setProduct(p.id)}>{p.name}</button>
                  ))}
                </div>
              </div>
              <Field
                label="Сумма, ₽"
                inputMode="numeric"
                value={terms.amount}
                onChange={(e) => setTerms({ ...terms, amount: e.target.value.replace(/\D/g, '') })}
                hint={product && `От ${formatRub(product.minAmount)} до ${formatRub(product.maxAmount)}`}
                error={errors.amount}
              />
              <div className="stack" style={{ gap: 'var(--space-3)' }}>
                <div className="muted small">Срок</div>
                <div className="chips">
                  {termOptions.map((t) => (
                    <button key={t} type="button" className="chip" aria-pressed={terms.termMonths === t} onClick={() => setTerms({ ...terms, termMonths: t })}>{t} мес.</button>
                  ))}
                </div>
              </div>
              <div className="stack" style={{ gap: 'var(--space-3)' }}>
                <div className="muted small">Цель</div>
                <div className="chips">
                  {PURPOSES.map((p) => (
                    <button key={p.value} type="button" className="chip" aria-pressed={terms.purpose === p.value} onClick={() => setTerms({ ...terms, purpose: p.value })}>{p.label}</button>
                  ))}
                </div>
              </div>
              {payment && (
                <div className="terms">
                  <div className="term"><div className="muted term__label">Ставка</div><div className="term__value">от {formatPercent(product.rateFrom)}</div></div>
                  <div className="term"><div className="muted term__label">Срок</div><div className="term__value">{formatMonths(terms.termMonths)}</div></div>
                  <div className="term"><div className="muted term__label">Платёж</div><div className="term__value">от {formatRub(payment)}</div></div>
                </div>
              )}
              <div className="row">
                <Button variant="secondary" onClick={() => setStep(1)}>Назад</Button>
                <Button onClick={next}>Далее</Button>
              </div>
            </>
          )}

          {step === 3 && company && (
            <>
              <h2>Проверьте и отправьте</h2>
              <dl className="kv-grid">
                <div><dt>Компания</dt><dd>{company.name}</dd></div>
                <div><dt>Продукт</dt><dd>{product?.name}</dd></div>
                <div><dt>Цель</dt><dd>{purposeLabel}</dd></div>
                <div><dt>Сумма</dt><dd>{formatRub(amount)}</dd></div>
                <div><dt>Срок</dt><dd>{formatMonths(terms.termMonths)}</dd></div>
                <div><dt>Контакт</dt><dd>{contact.name}, {contact.phone}</dd></div>
              </dl>
              <div className="stack" style={{ gap: 'var(--space-3)' }}>
                {CONSENTS.map((c) => (
                  <label key={c.key} className="check">
                    <input type="checkbox" checked={consents[c.key]} onChange={(e) => setConsents({ ...consents, [c.key]: e.target.checked })} />
                    <span>{c.label}</span>
                  </label>
                ))}
                {errors.consents && <p className="field__hint field__hint--error m0"><span aria-hidden="true">✕ </span>{errors.consents}</p>}
              </div>
              <div className="row">
                <Button variant="secondary" onClick={() => setStep(2)}>Назад</Button>
                <Button variant="accent" onClick={submit} disabled={submitting}>Отправить заявку</Button>
              </div>
            </>
          )}
        </Card>

        <aside className="stack">
          <AiHint>
            {step === 2
              ? 'Банк одобрит сумму, если платежи по всем кредитам вместе с новым не превысят половины среднемесячной выручки.'
              : 'Решение придёт в кабинет: вы увидите, какие показатели на него повлияли и как улучшить условия.'}
          </AiHint>
          <Card className="stack">
            <h3>Что учитывает банк</h3>
            <ul className="m0">
              <li>Выручку и её динамику за 12 месяцев</li>
              <li>Платежи по текущим кредитам</li>
              <li>Кредитную историю за 2 года</li>
              <li>Срок работы бизнеса</li>
            </ul>
          </Card>
        </aside>
      </div>
    </Page>
  );
}
