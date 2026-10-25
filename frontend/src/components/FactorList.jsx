// Факторы решения из API (factors[]). Знак + / − дублирует цвет.
const SIGN = { positive: '+', negative: '−', neutral: '•' };
const IMPACT = { positive: 'Повышает шансы', negative: 'Снижает шансы', neutral: 'Нейтрально' };
const WEIGHT = { high: 'Сильно', medium: 'Средне', low: 'Слабо' };

export default function FactorList({ factors }) {
  return (
    <ul className="factors">
      {factors.map((f) => (
        <li key={f.code} className={`factor factor--${f.impact}`}>
          <span className="factor__icon" aria-hidden="true">{SIGN[f.impact]}</span>
          <div className="factor__text">
            <div className="factor__label"><span className="sr-only">{IMPACT[f.impact]}: </span>{f.label}</div>
            <div className="factor__detail">{f.detail}</div>
          </div>
          <span className="factor__weight">{WEIGHT[f.weight]}</span>
        </li>
      ))}
    </ul>
  );
}

export function FactorLegend() {
  return (
    <div className="legend">
      <span>+ повышает шансы</span>
      <span>− снижает шансы</span>
      <span>Сила влияния: сильно / средне / слабо</span>
    </div>
  );
}
