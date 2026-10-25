import { ArtDefs, Coin, Glow, Line, Paper, Sparkle, useArtId } from './parts.jsx';

const ROWS = [
  { y: 218, a: 62, b: 70 },
  { y: 258, a: 74, b: 48 },
  { y: 298, a: 52, b: 66 },
];

// Заявка по ИНН: документ с полем ИНН и подтянутыми реквизитами, лупа, отметка «найдено»
export default function ArtDocument() {
  const id = useArtId('document');
  return (
    <svg viewBox="0 0 520 420" className="art" focusable="false">
      <ArtDefs id={id} />
      <Glow id={id} tone="aqua" cx={300} cy={230} r={230} />
      <Glow id={id} tone="violet" cx={110} cy={90} r={130} />

      <g transform="rotate(-6 250 220)">
        <Paper id={id} x={118} y={46} w={262} h={330} r={26} />
        <rect x={144} y={74} width={30} height={30} rx={9} fill="#EF3124" />
        <Line x={186} y={78} w={120} />
        <Line x={186} y={96} w={76} h={8} tone="#DCE1E8" />
        {/* Поле ИНН — как «заливочное» поле в кабинете */}
        <rect x={144} y={128} width={210} height={66} rx={10} fill="#E9EDF2" />
        <rect x={144} y={192} width={210} height={2} fill="#212124" />
        <text x={158} y={150} fontSize="12" fill="#6B7079">ИНН</text>
        <text x={158} y={178} fontSize="21" fontWeight="800" fill="#212124" letterSpacing="0.5">7701 000 001</text>
        {/* Подтянутые реквизиты */}
        {ROWS.map((r) => (
          <g key={r.y}>
            <rect x={144} y={r.y} width={100} height={30} rx={8} fill="#FFFFFF" />
            <rect x={252} y={r.y} width={102} height={30} rx={8} fill="#FFFFFF" />
            <Line x={154} y={r.y + 11} w={r.a} h={8} />
            <Line x={262} y={r.y + 11} w={r.b} h={8} />
          </g>
        ))}
        <rect x={144} y={340} width={120} height={14} rx={7} fill="#212124" />
      </g>

      {/* Отметка «компания найдена» */}
      <Coin id={id} cx={378} cy={78} r={42} tone="aqua" glyph={false} />
      <path d="M359 80l13 13 25-27" fill="none" stroke="#FFFFFF" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />

      {/* Лупа */}
      <rect x={404} y={318} width={84} height={28} rx={14} fill={`url(#${id}-graphite)`} transform="rotate(45 404 332)" />
      <circle cx={360} cy={286} r={64} fill="#88DBDF" fillOpacity="0.16" />
      <circle cx={360} cy={286} r={64} fill="none" stroke={`url(#${id}-steel)`} strokeWidth="16" />
      <path d="M322 262a46 46 0 0 1 34-24" fill="none" stroke="#FFFFFF" strokeOpacity="0.8" strokeWidth="7" strokeLinecap="round" />

      <Sparkle id={id} x={96} y={74} size={44} />
      <Sparkle id={id} x={136} y={34} size={18} />
    </svg>
  );
}
