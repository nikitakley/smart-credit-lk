import { ArtDefs, Coin, Glow, Line, Paper, Sparkle, useArtId } from './parts.jsx';

// Рост бизнеса: карточка с графиком, монета ₽, искры ИИ
export default function ArtGrowth() {
  const id = useArtId('growth');
  return (
    <svg viewBox="0 0 520 420" className="art" focusable="false">
      <ArtDefs id={id} />
      <Glow id={id} tone="red" cx={340} cy={260} r={230} />
      <Glow id={id} tone="violet" cx={130} cy={110} r={150} />

      <g transform="rotate(-8 240 215)">
        <Paper id={id} x={84} y={104} w={300} h={214} r={26} />
        <Line x={112} y={132} w={96} />
        <Line x={112} y={152} w={60} h={8} tone="#DCE1E8" />
        {[192, 222, 252, 282].map((y) => (
          <line key={y} x1={112} x2={356} y1={y} y2={y} stroke="#C2CAD5" strokeWidth="2" strokeDasharray="1 9" strokeLinecap="round" />
        ))}
        <path d="M112 284C142 280 160 252 188 254S232 274 256 242S304 216 356 182" fill="none" stroke="#88DBDF" strokeWidth="10" strokeLinecap="round" />
        <path d="M112 298C144 294 170 284 198 268S246 260 272 234S316 192 356 150" fill="none" stroke="#EF3124" strokeWidth="10" strokeLinecap="round" />
        <circle cx={356} cy={150} r={13} fill="#FFFFFF" stroke="#EF3124" strokeWidth="7" />
      </g>

      <Coin id={id} cx={438} cy={122} r={46} tone="aqua" glyph={false} />
      <Coin id={id} cx={394} cy={300} r={88} />
      <Sparkle id={id} x={92} y={86} size={58} />
      <Sparkle id={id} x={142} y={40} size={24} />
    </svg>
  );
}
