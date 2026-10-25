import { useId } from 'react';

// «Заливочное» поле как на alfabank.ru: лейбл внутри сверху, значение жирным, линия снизу.
// autofilled — данные подтянуты по ИНН, только чтение (белая плашка без линии).
// error — красная линия + иконка + текст: статус не передаём только цветом.
export default function Field({ label, hint, error, autofilled, className = '', ...input }) {
  const id = useId();
  const hintId = `${id}-hint`;
  const cls = ['field', autofilled && 'field--autofilled', error && 'field--error', className].filter(Boolean).join(' ');

  return (
    <div className={cls}>
      <div className="field__box">
        <label className="field__label" htmlFor={id}>{label}</label>
        <input
          id={id}
          className="field__input"
          readOnly={autofilled}
          aria-invalid={error ? true : undefined}
          aria-describedby={error || hint ? hintId : undefined}
          {...input}
        />
      </div>
      {error
        ? <div id={hintId} className="field__hint field__hint--error"><span aria-hidden="true">✕ </span>{error}</div>
        : hint && <div id={hintId} className="field__hint">{hint}</div>}
    </div>
  );
}
