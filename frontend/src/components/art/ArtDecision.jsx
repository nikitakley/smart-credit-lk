import { ArtDefs, Coin, Glow, Line, Paper, Sparkle, useArtId } from './parts.jsx';

// Как в FactorList: знак дублирует цвет
const ROWS = [
  { sign: '−', part: 0.82, bar: '#EF3124', tint: '#FDE3E0', ink: '#C8221A' },
  { sign: '+', part: 0.74, bar: '#88DBDF', tint: '#DDF4F5', ink: '#1C6F75' },
  { sign: '+', part: 0.56, bar: '#88DBDF', tint: '#DDF4F5', ink: '#1C6F75' },
  { sign: '•', part: 0.3, bar: '#B9C0CA', tint: '#ECEFF3', ink: '#646466' },
];

// Объяснимость: карточка факторов решения и пузырь объяснения ИИ
export default function ArtDecision() {
  const id = useArtId('decision');
  return (
    <svg viewBox="0 0 520 420" className="art" focusable="false">
      <ArtDefs id={id} />
      <Glow id={id} tone="red" cx={380} cy={160} r={210} />
      <Glow id={id} tone="violet" cx={150} cy={300} r={190} />

      <g transform="rotate(5 290 200)">
        <Paper id={id} x={140} y={60} w={320} h={262} r={26} />
        <Line x={168} y={88} w={150} />
        <Line x={168} y={108} w={92} h={8} tone="#DCE1E8" />
        {ROWS.map((r, i) => {
          const y = 140 + i * 44;
          return (
            <g key={i}>
              <circle cx={182} cy={y + 12} r={15} fill={r.tint} />
              <text x={182} y={y + 18} textAnchor="middle" fontSize="18" fontWeight="800" fill={r.ink}>{r.sign}</text>
              <rect x={208} y={y + 6} width={224} height={12} rx={6} fill="#E3E8EE" />
              <rect x={208} y={y + 6} width={224 * r.part} height={12} rx={6} fill={r.bar} />
            </g>
          );
        })}
      </g>

      {/* Пузырь объяснения ИИ */}
      <path d="M76 344l-16 30 40-26z" fill="#7B3BE0" />
      <rect x={40} y={238} width={200} height={110} rx={28} fill={`url(#${id}-violet)`} />
      <Sparkle id={id} x={72} y={271} size={26} fill="#FFFFFF" />
      <Line x={96} y={266} w={116} h={10} tone="rgba(255,255,255,0.85)" />
      <Line x={62} y={296} w={154} h={9} tone="rgba(255,255,255,0.55)" />
      <Line x={62} y={316} w={120} h={9} tone="rgba(255,255,255,0.55)" />

      <Coin id={id} cx={456} cy={74} r={40} />
      <Sparkle id={id} x={300} y={366} size={30} />
    </svg>
  );
}
