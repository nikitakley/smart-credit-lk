// Шаги строятся через buildTimeline() из config/statuses.js.
// step: { key, label, state: done | current | warning | error | upcoming, date?, note? }

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
          </div>
        </li>
      ))}
    </ol>
  );
}
