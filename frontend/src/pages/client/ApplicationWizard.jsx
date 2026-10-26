import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import AiHint from '../../components/AiHint.jsx';
import Badge from '../../components/Badge.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import Field from '../../components/Field.jsx';
import Page from '../../components/Page.jsx';
import ArtDocument from '../../components/art/ArtDocument.jsx';
import {
  createDraft, fieldErrors, getApplication, getDictionaries, getMyCompany, getProducts, submitApplication, updateDraft,
} from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';
import { annuity, formatDate, formatMonths, formatPercent, formatRub } from '../../lib/format.js';

const STEPS = ['Компания', 'Контакты', 'Условия', 'Отправка'];
const TERMS = [3, 6, 12, 18, 24, 36, 48, 60];
const CONSENTS = [
  { key: 'bki', label: 'Согласие на запрос в бюро кредитных историй' },
  { key: 'personalData', label: 'Согласие на обработку персональных данных' },
];
// На каком шаге поле — чтобы вернуть клиента к ошибке, которую нашёл сервер
const FIELD_STEP = { contact: 1, productId: 2, amount: 2, termMonths: 2, purpose: 2, collateral: 2 };

export default function ApplicationWizard() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const { data: company, error: companyError } = useLoad(getMyCompany, []);
  const { data: products } = useLoad(getProducts, []);
  const { data: dicts, error: dictsError } = useLoad(getDictionaries, []);

  const [draftId, setDraftId] = useState(params.get('draft'));
  const [step, setStep] = useState(0);
  const [contact, setContact] = useState(null);
  const [terms, setTerms] = useState({
    productId: params.get('product') ?? 'working-capital',
    amount: params.get('amount') ?? '2000000',
    termMonths: Number(params.get('term')) || 24,
    purpose: params.get('purpose') ?? 'working_capital',
    collateral: params.get('collateral') ?? 'none',
  });
  const [consents, setConsents] = useState({ bki: false, personalData: false });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [busy, setBusy] = useState(false);
  const idempotencyKey = useRef(crypto.randomUUID());

  // Продолжение черновика: подставляем то, что уже сохранено на сервере
  useEffect(() => {
    const id = params.get('draft');
    if (!id) return;
    getApplication(id).then((app) => {
      if (app.status !== 'draft') { navigate(`/applications/${app.id}`, { replace: true }); return; }
      setTerms((t) => ({
        productId: app.productId ?? t.productId,
        amount: app.amount != null ? String(app.amount) : t.amount,
        termMonths: app.termMonths ?? t.termMonths,
        purpose: app.purpose ?? t.purpose,
        collateral: app.collateral ?? t.collateral,
      }));
      if (app.contact) setContact(app.contact);
    }).catch((err) => setFormError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Контакты по умолчанию — из профиля компании
  useEffect(() => {
    if (company && !contact) setContact({ name: company.director, phone: company.phone, email: company.email });
  }, [company, contact]);

  const product = products?.find((p) => p.id === terms.productId);
  const amount = Number(terms.amount) || 0;
  const termOptions = TERMS.filter((t) => !product || t <= product.maxTermMonths);
  const payment = product && amount > 0 ? annuity(amount, product.rateFrom, terms.termMonths) : null;

  // Срок из помощника может быть больше, чем позволяет продукт — прижимаем к максимуму
  useEffect(() => {
    if (product && terms.termMonths > product.maxTermMonths) setTerms((t) => ({ ...t, termMonths: product.maxTermMonths }));
  }, [product, terms.termMonths]);

  const termsPayload = () => ({ ...terms, amount });

  const validateLocal = () => {
    const e = {};
    if (step === 1) {
      if (!contact.name.trim()) e.name = 'Укажите контактное лицо';
      if (!/^\+?[\d\s()-]{10,}$/.test(contact.phone)) e.phone = 'Телефон в формате +7 900 000-00-00';
      if (!/^\S+@\S+\.\S+$/.test(contact.email)) e.email = 'Проверьте email';
    }
    if (step === 2 && product && (amount < product.minAmount || amount > product.maxAmount)) {
      e.amount = `От ${formatRub(product.minAmount)} до ${formatRub(product.maxAmount)} для этого продукта`;
    }
    if (step === 3 && !(consents.bki && consents.personalData)) e.consents = 'Без согласий банк не сможет рассмотреть заявку';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  // Ошибка сервера: поля → подсказки у полей, клиента возвращаем на шаг с первой ошибкой
  const showServerError = (err) => {
    if (err.code === 'not_draft' && draftId) { navigate(`/applications/${draftId}`, { replace: true }); return; }
    const f = fieldErrors(err);
    const mapped = {
      amount: f.amount ?? f.termMonths ?? f.productId ?? f.purpose,
      name: f.contact ?? f['contact.name'], phone: f['contact.phone'], email: f['contact.email'],
      consents: f['consents.bki'] ?? f['consents.personalData'],
    };
    setErrors(Object.fromEntries(Object.entries(mapped).filter(([, v]) => v)));
    setFormError(err.fields?.length ? null : err.message);
    const back = Math.min(...Object.keys(f).map((k) => FIELD_STEP[k.split('.')[0]] ?? 99));
    if (back < step) setStep(back);
  };

  const run = async (fn) => {
    setBusy(true);
    setFormError(null);
    try { await fn(); } catch (err) { showServerError(err); } finally { setBusy(false); }
  };

  // Шаг 1: черновик создаётся сразу — дальше каждый шаг сохраняется на сервере
  const confirmCompany = () => run(async () => {
    if (!draftId) {
      const draft = await createDraft({ ...termsPayload(), contact });
      setDraftId(draft.id);
      setParams((p) => { p.set('draft', draft.id); return p; }, { replace: true });
    }
    setStep(1);
  });

  const saveContact = () => validateLocal() && run(async () => { await updateDraft(draftId, { contact }); setStep(2); });
  const saveTerms = () => validateLocal() && run(async () => { await updateDraft(draftId, termsPayload()); setStep(3); });
  const submit = () => validateLocal() && run(async () => {
    const app = await submitApplication(draftId, consents, idempotencyKey.current);
    navigate(`/applications/${app.id}`);
  });

  const setProduct = (productId) => {
    const p = products.find((x) => x.id === productId);
    setTerms((t) => ({ ...t, productId, termMonths: Math.min(t.termMonths, p.maxTermMonths) }));
  };

  const purposes = dicts?.purposes ?? [];
  const collaterals = dicts?.collateralTypes ?? [];
  const labelOf = (list, code) => list.find((x) => x.code === code)?.label ?? code;

  return (
    <Page
      title="Заявка на кредит"
      subtitle={`${product?.name ?? 'Кредит для бизнеса'} · шаг ${step + 1} из ${STEPS.length}.${draftId ? ` Черновик ${draftId} сохраняется автоматически.` : ' Реквизиты компании уже подтянули.'}`}
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
          {formError && <p className="m0 caveat"><span aria-hidden="true">! </span>{formError}</p>}
          {dictsError && step === 2 && <p className="m0 caveat"><span aria-hidden="true">! </span>Не удалось загрузить цели и виды залога: {dictsError.message}</p>}

          {step === 0 && (
            <>
              <h2>Реквизиты компании</h2>
              {companyError && <p className="m0 caveat">{companyError.message}</p>}
              {!company && !companyError && <p className="muted m0">Получаем реквизиты компании…</p>}
              {company && (
                <>
                  <div className="row">
                    <Badge tone="success">Данные получены</Badge>
                    <span className="muted small">по данным {company.source ?? 'ФНС'} на {formatDate(company.fetchedAt)}</span>
                  </div>
                  <div className="fields-2">
                    <Field autofilled label="ИНН" value={company.inn} />
                    <Field autofilled label="Название" value={company.name} />
                    <Field autofilled className="span-2" label="Полное наименование" value={company.fullName} />
                    <Field autofilled label={company.type === 'ip' ? 'ОГРНИП' : 'ОГРН'} value={company.ogrn} />
                    {company.kpp && <Field autofilled label="КПП" value={company.kpp} />}
                    <Field autofilled label="Дата регистрации" value={formatDate(company.registeredAt)} />
                    <Field autofilled label={company.directorTitle ?? 'Руководитель'} value={company.director} />
                    <Field autofilled className="span-2" label="ОКВЭД" value={`${company.okved.code} — ${company.okved.title}`} />
                    <Field autofilled className="span-2" label="Юридический адрес" value={company.legalAddress} />
                    {company.founders?.length > 0 && (
                      <Field autofilled className="span-2" label="Учредители" value={company.founders.map((f) => `${f.name} — ${f.sharePercent}%`).join(', ')} />
                    )}
                  </div>
                  <p className="muted small m0">Вы вошли как клиент банка, поэтому вводить ИНН и реквизиты не нужно.</p>
                  <div className="row"><Button disabled={busy} onClick={confirmCompany}>Всё верно, дальше</Button></div>
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
                <Button disabled={busy} onClick={saveContact}>Далее</Button>
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
                  {purposes.map((p) => (
                    <button key={p.code} type="button" className="chip" aria-pressed={terms.purpose === p.code} onClick={() => setTerms({ ...terms, purpose: p.code })}>{p.label}</button>
                  ))}
                </div>
              </div>
              <div className="stack" style={{ gap: 'var(--space-3)' }}>
                <div className="muted small">Залог</div>
                <div className="chips">
                  {collaterals.map((c) => (
                    <button key={c.code} type="button" className="chip" aria-pressed={terms.collateral === c.code} onClick={() => setTerms({ ...terms, collateral: c.code })}>{c.label}</button>
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
                <Button disabled={busy} onClick={saveTerms}>Далее</Button>
              </div>
            </>
          )}

          {step === 3 && company && contact && (
            <>
              <h2>Проверьте и отправьте</h2>
              <dl className="kv-grid">
                <div><dt>Компания</dt><dd>{company.name}</dd></div>
                <div><dt>Продукт</dt><dd>{product?.name}</dd></div>
                <div><dt>Цель</dt><dd>{labelOf(purposes, terms.purpose)}</dd></div>
                <div><dt>Сумма</dt><dd>{formatRub(amount)}</dd></div>
                <div><dt>Срок</dt><dd>{formatMonths(terms.termMonths)}</dd></div>
                <div><dt>Залог</dt><dd>{labelOf(collaterals, terms.collateral)}</dd></div>
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
                <Button variant="accent" onClick={submit} disabled={busy}>Отправить заявку</Button>
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
            <h3>Что проверит банк</h3>
            <ul className="m0">
              <li>Обороты по счёту в банке</li>
              <li>Данные ЕГРЮЛ / ЕГРИП</li>
              <li>ФНС «Прозрачный бизнес»</li>
              <li>Кредитную историю в БКИ</li>
            </ul>
          </Card>
        </aside>
      </div>
    </Page>
  );
}
