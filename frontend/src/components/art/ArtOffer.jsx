import { ArtDefs, Coin, FlatCoin, Glow, Paper, Sparkle, useArtId } from './parts.jsx';

// Предложение банка: стопка монет, монета ₽, бирка со ставкой
export default function ArtOffer() {
  const id = useArtId('offer');
  return (
    <svg viewBox="0 0 520 420" className="art" focusable="false">
      <ArtDefs id={id} />
      <Glow id={id} tone="red" cx={320} cy={240} r={240} />
      <Glow id={id} tone="aqua" cx={120} cy={330} r={150} />

      {[0, 1, 2, 3].map((i) => (
        <FlatCoin key={i} id={id} cx={180} cy={344 - i * 26} rx={92} ry={30} h={20} />
      ))}
      <Coin id={id} cx={352} cy={212} r={112} />

      <g transform="rotate(-12 150 110)">
        <Paper id={id} x={74} y={64} w={154} h={92} r={24} />
        <text x={151} y={129} textAnchor="middle" fontSize="54" fontWeight="800" fill="#EF3124">%</text>
      </g>

      <Coin id={id} cx={472} cy={352} r={36} tone="aqua" glyph={false} />
      <Sparkle id={id} x={474} y={68} size={44} />
      <Sparkle id={id} x={438} y={32} size={18} />
    </svg>
  );
}
