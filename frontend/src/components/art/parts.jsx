import { useId } from 'react';

// Детали иллюстраций для hero. Иллюстрации свои (не с сайта банка), цвета — из брендбука:
// красный #EF3124, аква #88DBDF и фиолетовый #6A22D0 из доп. палитры, белый и металлик.
// Единственное место, где цвета заданы HEX напрямую: градиенты внутри SVG не читают CSS-переменные.

// Уникальный префикс id градиентов — чтобы две иллюстрации на странице не конфликтовали
export function useArtId(name) {
  return `${name}-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
}

export function ArtDefs({ id }) {
  return (
    <defs>
      <radialGradient id={`${id}-glow-red`}>
        <stop offset="0" stopColor="#EF3124" stopOpacity="0.5" />
        <stop offset="1" stopColor="#EF3124" stopOpacity="0" />
      </radialGradient>
      <radialGradient id={`${id}-glow-aqua`}>
        <stop offset="0" stopColor="#88DBDF" stopOpacity="0.4" />
        <stop offset="1" stopColor="#88DBDF" stopOpacity="0" />
      </radialGradient>
      <radialGradient id={`${id}-glow-violet`}>
        <stop offset="0" stopColor="#7B3BE0" stopOpacity="0.55" />
        <stop offset="1" stopColor="#7B3BE0" stopOpacity="0" />
      </radialGradient>
      <linearGradient id={`${id}-red-face`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#FF8A7F" />
        <stop offset="0.45" stopColor="#EF3124" />
        <stop offset="1" stopColor="#B4170D" />
      </linearGradient>
      <linearGradient id={`${id}-red-edge`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#B4170D" />
        <stop offset="1" stopColor="#6E0B05" />
      </linearGradient>
      <linearGradient id={`${id}-aqua-face`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#E3FAFB" />
        <stop offset="0.5" stopColor="#88DBDF" />
        <stop offset="1" stopColor="#3AA9B0" />
      </linearGradient>
      <linearGradient id={`${id}-aqua-edge`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#3AA9B0" />
        <stop offset="1" stopColor="#1C6F75" />
      </linearGradient>
      <linearGradient id={`${id}-paper`} x1="0" y1="0" x2="0.3" y2="1">
        <stop offset="0" stopColor="#FFFFFF" />
        <stop offset="1" stopColor="#DCE2EA" />
      </linearGradient>
      <linearGradient id={`${id}-violet`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#B795FF" />
        <stop offset="1" stopColor="#6A22D0" />
      </linearGradient>
      <linearGradient id={`${id}-steel`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#FFFFFF" />
        <stop offset="0.5" stopColor="#C4C9D1" />
        <stop offset="1" stopColor="#7D8187" />
      </linearGradient>
      <linearGradient id={`${id}-graphite`} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#4A4E55" />
        <stop offset="1" stopColor="#141518" />
      </linearGradient>
    </defs>
  );
}

export function Glow({ id, tone, cx, cy, r }) {
  return <circle cx={cx} cy={cy} r={r} fill={`url(#${id}-glow-${tone})`} />;
}

// Знак ₽ штрихами в квадрате 100×100, центр ≈ (49, 53)
export function Ruble({ cx, cy, size, color = '#FFFFFF' }) {
  const s = size / 100;
  return (
    <path
      d="M36 86V20H57a19 19 0 0 1 0 38H36M22 71H62"
      fill="none" stroke={color} strokeWidth="11" strokeLinecap="round" strokeLinejoin="round"
      transform={`translate(${cx - 49 * s} ${cy - 53 * s}) scale(${s})`}
    />
  );
}

// Монета анфас «с толщиной»: ребро — смещённый круг темнее, лицевая сторона с бликом
export function Coin({ id, cx, cy, r, tone = 'red', glyph = true }) {
  const d = r * 0.11;
  return (
    <g>
      <circle cx={cx + d * 0.7} cy={cy + d} r={r} fill={`url(#${id}-${tone}-edge)`} />
      <circle cx={cx} cy={cy} r={r} fill={`url(#${id}-${tone}-face)`} />
      <circle cx={cx} cy={cy} r={r * 0.8} fill="none" stroke="#FFFFFF" strokeOpacity="0.3" strokeWidth={Math.max(1.5, r * 0.035)} />
      <ellipse
        cx={cx - r * 0.38} cy={cy - r * 0.46} rx={r * 0.32} ry={r * 0.13} fill="#FFFFFF" opacity="0.38"
        transform={`rotate(-35 ${cx - r * 0.38} ${cy - r * 0.46})`}
      />
      {glyph && <Ruble cx={cx} cy={cy} size={r * 0.95} />}
    </g>
  );
}

// Монета плашмя — для стопок
export function FlatCoin({ id, cx, cy, rx, ry, h, tone = 'red' }) {
  return (
    <g>
      <path d={`M${cx - rx} ${cy}v${h}a${rx} ${ry} 0 0 0 ${2 * rx} 0v${-h}Z`} fill={`url(#${id}-${tone}-edge)`} />
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill={`url(#${id}-${tone}-face)`} />
      <ellipse cx={cx} cy={cy} rx={rx * 0.76} ry={ry * 0.66} fill="none" stroke="#FFFFFF" strokeOpacity="0.32" strokeWidth={Math.max(1, ry * 0.1)} />
    </g>
  );
}

// Четырёхлучевая искра — знак ИИ-помощника
export function Sparkle({ id, x, y, size, fill }) {
  const s = size / 2;
  const k = s * 0.16;
  const d = `M${x} ${y - s}C${x + k} ${y - k} ${x + k} ${y - k} ${x + s} ${y}`
    + `C${x + k} ${y + k} ${x + k} ${y + k} ${x} ${y + s}`
    + `C${x - k} ${y + k} ${x - k} ${y + k} ${x - s} ${y}`
    + `C${x - k} ${y - k} ${x - k} ${y - k} ${x} ${y - s}Z`;
  return <path d={d} fill={fill ?? `url(#${id}-violet)`} />;
}

// Бумажная карточка с бликом по кромке
export function Paper({ id, x, y, w, h, r = 24, opacity = 1 }) {
  return (
    <g opacity={opacity}>
      <rect x={x} y={y} width={w} height={h} rx={r} fill={`url(#${id}-paper)`} />
      <rect x={x + 0.5} y={y + 0.5} width={w - 1} height={h - 1} rx={r - 0.5} fill="none" stroke="#FFFFFF" strokeOpacity="0.9" />
    </g>
  );
}

// Серая «строка текста»
export function Line({ x, y, w, h = 10, tone = '#C9D0DA' }) {
  return <rect x={x} y={y} width={w} height={h} rx={h / 2} fill={tone} />;
}
