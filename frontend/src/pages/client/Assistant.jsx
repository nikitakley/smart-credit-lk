import { useState } from 'react';
import AiHint from '../../components/AiHint.jsx';
import Badge from '../../components/Badge.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import Page from '../../components/Page.jsx';
import ProductFacts from '../../components/ProductFacts.jsx';
import ProductIcon from '../../components/ProductIcon.jsx';
import ArtAssistant from '../../components/art/ArtAssistant.jsx';
import { recommend } from '../../api/client.js';

// Ответы — примерные диапазоны: точные цифры клиент укажет в заявке.
// value — то, что уходит в API (purpose и collateral — как enum в контракте)
const QUESTIONS = [
  {
    key: 'purpose', title: 'На что нужны деньги?',
    options: [
      { value: 'working_capital', label: 'Пополнить оборотные средства', hint: 'Закупки, зарплаты, налоги' },
      { value: 'cash_gap', label: 'Закрыть кассовый разрыв', hint: 'Клиенты платят позже, чем нужно платить вам' },
      { value: 'equipment', label: 'Купить оборудование или транспорт' },
      { value: 'renovation', label: 'Ремонт или расширение' },
    ],
  },
  {
    key: 'amount', title: 'Какая сумма нужна?',
    options: [
      { value: 400_000, label: 'До 500 тыс. ₽' },
      { value: 2_000_000, label: '500 тыс. – 3 млн ₽' },
      { value: 6_000_000, label: '3–10 млн ₽' },
      { value: 15_000_000, label: 'Больше 10 млн ₽' },
    ],
  },
  {
    key: 'termMonths', title: 'На какой срок?',
    options: [
      { value: 12, label: 'До года' },
      { value: 24, label: '1–3 года' },
      { value: 48, label: 'Больше 3 лет' },
    ],
  },
  {
    key: 'collateral', title: 'Есть что предложить в залог?',
    options: [
      { value: 'real_estate', label: 'Недвижимость' },
      { value: 'equipment', label: 'Оборудование или транспорт' },
      { value: 'none', label: 'Нет залога' },
    ],
  },
];

const HOW = [
  { title: 'Подберите продукт', text: 'Помощник задаст четыре вопроса и объяснит, почему продукт подходит.' },
  { title: 'Заполните заявку по ИНН', text: 'Реквизиты компании подтянем из ЕГРЮЛ — вручную вводить не нужно.' },
  { title: 'Получите решение с объяснением', text: 'Покажем, что повлияло на решение и как улучшить условия.' },
];

const labelOf = (q, value) => q.options.find((o) => o.value === value)?.label;

export default function Assistant() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null); // null | 'loading' | { summary, items }

  const q = QUESTIONS[step];

  const answer = async (value) => {
    const next = { ...answers, [q.key]: value };
    setAnswers(next);
    if (step < QUESTIONS.length - 1) { setStep(step + 1); return; }
    setResult('loading');
    setResult(await recommend(next));
  };

  const restart = () => { setStep(0); setAnswers({}); setResult(null); };

  return (
    <Page
      title="Подберём кредит под вашу задачу"
      subtitle="Ответьте на четыре вопроса — помощник предложит продукты и объяснит выбор. Это ни к чему не обязывает."
      actions={(
        <>
          <a href="#quiz" className="btn btn-accent btn--l">Начать подбор</a>
          <Button to="/catalog" variant="ondark" size="l">Все продукты</Button>
        </>
      )}
      art={<ArtAssistant />}
    >
      <section id="quiz" className="section">
        <h2 className="section-title">Подбор продукта</h2>
        <div className="columns">
          <div className="stack">
            {result === null && (
              <Card className="stack">
                <div className="stack" style={{ gap: 'var(--space-2)' }}>
                  <div className="muted small">Вопрос {step + 1} из {QUESTIONS.length}</div>
                  <div className="progress" aria-hidden="true">
                    <div className="progress__bar" style={{ width: `${(step / QUESTIONS.length) * 100}%` }} />
                  </div>
                </div>
                <h3>{q.title}</h3>
                <div className="choices" role="group" aria-label={q.title}>
                  {q.options.map((o) => (
                    <button key={o.value} type="button" className="choice" aria-pressed={answers[q.key] === o.value} onClick={() => answer(o.value)}>
                      <span className="choice__label">{o.label}</span>
                      {o.hint && <span className="choice__hint">{o.hint}</span>}
                    </button>
                  ))}
                </div>
                {step > 0 && <div className="row"><Button variant="secondary" onClick={() => setStep(step - 1)}>Назад</Button></div>}
              </Card>
            )}

            {result === 'loading' && <Card><p className="muted m0">Подбираем продукты…</p></Card>}

            {result && result !== 'loading' && (
              <>
                <AiHint label="Помощник">{result.summary}</AiHint>
                {result.items.map(({ product: p, best, reasons, caveat }) => (
                  <Card key={p.id} className="stack">
                    <div className="product-card__head">
                      <div className="stack" style={{ gap: 'var(--space-2)' }}>
                        {best && <div><Badge tone="success">Лучше всего подходит</Badge></div>}
                        <h3>{p.name}</h3>
                        <p className="muted m0">{p.note}</p>
                      </div>
                      <ProductIcon productId={p.id} />
                    </div>
                    <ProductFacts product={p} large />
                    <ul className="m0 reasons">{reasons.map((r) => <li key={r}>{r}</li>)}</ul>
                    {caveat && <p className="small m0 caveat"><span aria-hidden="true">! </span>{caveat}</p>}
                    <div className="row"><Button to={`/apply?product=${p.id}&amount=${answers.amount}&term=${answers.termMonths}&purpose=${answers.purpose}`} size="s" variant={best ? 'primary' : 'secondary'}>Оформить</Button></div>
                  </Card>
                ))}
                <div className="row">
                  <Button variant="secondary" onClick={restart}>Пройти заново</Button>
                  <Button variant="secondary" to="/catalog">Весь каталог</Button>
                </div>
              </>
            )}
          </div>

          <aside className="stack">
            {result === null && (
              <AiHint>Отвечайте примерно — точные цифры спросим в заявке. Подбор ни к чему не обязывает.</AiHint>
            )}
            {Object.keys(answers).length > 0 && (
              <Card className="stack">
                <h3>Ваши ответы</h3>
                <dl className="kv-grid kv-grid--1">
                  {QUESTIONS.filter((x) => x.key in answers).map((x) => (
                    <div key={x.key}><dt>{x.title}</dt><dd>{labelOf(x, answers[x.key])}</dd></div>
                  ))}
                </dl>
              </Card>
            )}
            <p className="muted small m0">Подбор по правилам: учитываем цель, сумму, срок и лимиты продуктов. Решение по заявке принимает банк.</p>
          </aside>
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">Как получить кредит</h2>
        <ol className="how">
          {HOW.map((s, i) => (
            <li key={s.title} className="how__step">
              <span className="how__num" aria-hidden="true">{i + 1}</span>
              <h3>{s.title}</h3>
              <p className="muted m0">{s.text}</p>
            </li>
          ))}
        </ol>
      </section>
    </Page>
  );
}
