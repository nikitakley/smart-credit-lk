import { ArtDefs, Glow, Line, Paper, Sparkle, useArtId } from './parts.jsx';

const BARS = [
  { y: 248, part: 0.8, fill: '#EF3124' },
  { y: 274, part: 0.55, fill: '#88DBDF' },
  { y: 300, part: 0.35, fill: '#88DBDF' },
];
const RING = 2 * Math.PI * 36;

// Очередь аналитика: стопка заявок со статусом, мини-шкала оценки и искры рекомендации ИИ
export default function ArtAnalyst() {
  const id = useArtId('analyst');
  return (
    <svg viewBox="0 0 520 420" className="art" focusable="false">
      <ArtDefs id={id} />
      <Glow id={id} tone="violet" cx={380} cy={140} r={210} />
      <Glow id={id} tone="red" cx={170} cy={320} r={190} />

      <g transform="rotate(-12 260 170)"><Paper id={id} x={120} y={70} w={300} h={170} r={24} opacity={0.5} /></g>
      <g transform="rotate(-5 260 200)"><Paper id={id} x={110} y={112} w={300} h={170} r={24} opacity={0.78} /></g>

      <Paper id={id} x={96} y={160} w={316} h={190} r={26} />
      <circle cx={140} cy={204} r={22} fill="#EF3124" />
      <text x={140} y={211} textAnchor="middle" fontSize="18" fontWeight="800" fill="#FFFFFF">Р</text>
      <Line x={174} y={192} w={110} />
      <Line x={174} y={210} w={70} h={8} tone="#DCE1E8" />
      <rect x={298} y={190} width={94} height={28} rx={14} fill="#FFF4E0" />
      <text x={345} y={209} textAnchor="middle" fontSize="12" fontWeight="700" fill="#9A5B00">Проверка</text>
      {BARS.map((b) => (
        <g key={b.y}>
          <rect x={122} y={b.y} width={170} height={10} rx={5} fill="#E3E8EE" />
          <rect x={122} y={b.y} width={170 * b.part} height={10} rx={5} fill={b.fill} />
        </g>
      ))}
      <circle cx={350} cy={282} r={36} fill="none" stroke="#E3E8EE" strokeWidth="11" />
      <circle
        cx={350} cy={282} r={36} fill="none" stroke="#EF3124" strokeWidth="11" strokeLinecap="round"
        strokeDasharray={`${RING * 0.64} ${RING}`} transform="rotate(-90 350 282)"
      />
      <text x={350} y={288} textAnchor="middle" fontSize="15" fontWeight="800" fill="#212124">640</text>

      <Sparkle id={id} x={438} y={126} size={60} />
      <Sparkle id={id} x={480} y={184} size={22} />
      <Sparkle id={id} x={404} y={70} size={16} />
    </svg>
  );
}
