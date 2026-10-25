import { ArtDefs, Coin, Glow, Paper, Sparkle, useArtId } from './parts.jsx';

const CHIPS = [
  { x: 52, w: 116, text: 'до 3 млн ₽', on: true },
  { x: 178, w: 96, text: '1–3 года' },
  { x: 284, w: 116, text: 'без залога' },
];

// Помощник подбора: вопрос клиента, ответ ИИ с продуктами, ответы-чипсы
export default function ArtAssistant() {
  const id = useArtId('assistant');
  return (
    <svg viewBox="0 0 520 420" className="art" focusable="false">
      <ArtDefs id={id} />
      <Glow id={id} tone="violet" cx={250} cy={200} r={240} />
      <Glow id={id} tone="red" cx={450} cy={330} r={150} />

      {/* Вопрос клиента */}
      <g transform="rotate(3 360 92)">
        <path d="M446 118l26 26-6-28z" fill="#E2E7EE" />
        <Paper id={id} x={232} y={56} w={252} h={66} r={24} />
        <text x={254} y={95} fontSize="15" fontWeight="700" fill="#212124">Нужны деньги на закупку</text>
      </g>

      {/* Ответ помощника */}
      <path d="M86 306l-20 30 42-24z" fill="#7B3BE0" />
      <rect x={52} y={150} width={318} height={164} rx={30} fill={`url(#${id}-violet)`} />
      <Sparkle id={id} x={84} y={183} size={22} fill="#FFFFFF" />
      <text x={102} y={188} fontSize="12" fontWeight="700" fill="#FFFFFF" fillOpacity="0.85" letterSpacing="0.8">ПОМОЩНИК</text>
      <rect x={74} y={206} width={274} height={42} rx={14} fill="#FFFFFF" />
      <circle cx={96} cy={227} r={7} fill="#EF3124" />
      <text x={112} y={232} fontSize="15" fontWeight="700" fill="#212124">Оборотный кредит</text>
      <text x={334} y={232} fontSize="12" fontWeight="700" fill="#177A3A" textAnchor="end">подходит</text>
      <rect x={74} y={256} width={274} height={42} rx={14} fill="#FFFFFF" fillOpacity="0.7" />
      <circle cx={96} cy={277} r={7} fill="#88DBDF" />
      <text x={112} y={282} fontSize="15" fontWeight="700" fill="#212124" fillOpacity="0.75">Овердрафт</text>

      {/* Ответы-чипсы */}
      {CHIPS.map((c) => (
        <g key={c.text}>
          <rect x={c.x} y={338} width={c.w} height={36} rx={18} fill="#FFFFFF" fillOpacity={c.on ? 1 : 0.14} />
          <text x={c.x + c.w / 2} y={361} textAnchor="middle" fontSize="13" fontWeight="600" fill={c.on ? '#212124' : '#FFFFFF'}>{c.text}</text>
        </g>
      ))}

      <Coin id={id} cx={450} cy={316} r={64} />
      <Sparkle id={id} x={470} y={190} size={40} />
      <Sparkle id={id} x={500} y={232} size={16} />
    </svg>
  );
}
