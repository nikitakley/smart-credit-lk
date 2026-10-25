import { useArtId } from './parts.jsx';

const R = 116;
const C = 2 * Math.PI * R;
const TONES = {
  red: ['#FF8A7F', '#EF3124'],
  aqua: ['#E3FAFB', '#88DBDF'],
};

// Кольцевая шкала для hero на данных из API: оценка модели, пройденные этапы заявки
export default function RingGauge({ ratio, value, caption, tone = 'red' }) {
  const id = useArtId('gauge');
  const part = Math.max(0, Math.min(1, ratio));
  const [from, to] = TONES[tone] ?? TONES.red;
  return (
    <svg viewBox="0 0 520 420" className="art" focusable="false">
      <defs>
        <linearGradient id={`${id}-arc`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={from} />
          <stop offset="1" stopColor={to} />
        </linearGradient>
        <radialGradient id={`${id}-glow`}>
          <stop offset="0" stopColor={to} stopOpacity="0.35" />
          <stop offset="1" stopColor={to} stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx={300} cy={196} r={210} fill={`url(#${id}-glow)`} />
      <circle cx={300} cy={196} r={R} fill="none" stroke="#FFFFFF" strokeOpacity="0.12" strokeWidth="24" />
      <circle
        cx={300} cy={196} r={R} fill="none" stroke={`url(#${id}-arc)`} strokeWidth="24" strokeLinecap="round"
        strokeDasharray={`${C * part} ${C}`} transform="rotate(-90 300 196)"
      />
      <text x={300} y={212} textAnchor="middle" fontSize="58" fontWeight="800" fill="#FFFFFF">{value}</text>
      <text x={300} y={244} textAnchor="middle" fontSize="15" fill="#FFFFFF" fillOpacity="0.64">{caption}</text>
    </svg>
  );
}
