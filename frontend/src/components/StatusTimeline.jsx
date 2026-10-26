// Шаги строятся через buildTimeline() из config/statuses.js.
// step: { key, label, state: done | current | warning | error | upcoming, date?, note?, marks?: [{ date, note, actor }] }
// marks — события без смены статуса (например, повторный запрос данных из источников)

const MARKERS = { done: '✓', current: '•', warning: '!', error: '✕', upcoming: '' };

export default function StatusTimeline({ steps }) {
  return (
    <ol className="timeline">
      {steps.map((step, i) => (
        <li
          key={`${step.key}-${i}`}
          className={`timeline__step timeline__step--${step.state}`}
          aria-current={step.state === 'current' ? 'step' : undefined}
        >
          <span className="timeline__marker" aria-hidden="true">{MARKERS[step.state]}</span>
          <div className="timeline__body">
            <div className="timeline__label">{step.label}</div>
            {step.date && <div className="timeline__meta">{step.date}</div>}
            {step.note && <div className="timeline__meta">{step.note}</div>}
            {step.marks?.length > 0 && (
              <ul className="timeline__marks">
                {step.marks.map((m, j) => (
                  <li key={j} className="timeline__mark">
                    <span aria-hidden="true">↻ </span>{m.note ?? 'Событие'}
                    <span className="timeline__meta"> · {m.date}{m.actor ? `, ${m.actor}` : ''}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
