import { ArtDefs, Coin, FlatCoin, useArtId } from './art/parts.jsx';

// Иконки продуктов для каталога и помощника — в стиле иллюстраций hero
export default function ProductIcon({ productId }) {
  const id = useArtId('product');
  return (
    <svg viewBox="0 0 64 64" className="product-icon" aria-hidden="true" focusable="false">
      <ArtDefs id={id} />
      {productId === 'working-capital' && (
        <>
          <FlatCoin id={id} cx={28} cy={46} rx={18} ry={6} h={5} />
          <FlatCoin id={id} cx={28} cy={38} rx={18} ry={6} h={5} />
          <FlatCoin id={id} cx={28} cy={30} rx={18} ry={6} h={5} />
          <Coin id={id} cx={46} cy={20} r={11} tone="aqua" glyph={false} />
        </>
      )}
      {productId === 'investment' && (
        <>
          <rect x={10} y={36} width={11} height={18} rx={3} fill={`url(#${id}-aqua-face)`} />
          <rect x={26} y={27} width={11} height={27} rx={3} fill={`url(#${id}-aqua-face)`} />
          <rect x={42} y={18} width={11} height={36} rx={3} fill={`url(#${id}-red-face)`} />
          <path d="M10 27L26 16l9 6 18-13" fill="none" stroke="#EF3124" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        </>
      )}
      {productId === 'overdraft' && (
        <>
          <rect x={8} y={16} width={42} height={30} rx={7} fill={`url(#${id}-graphite)`} />
          <rect x={8} y={22} width={42} height={6} fill="#000000" opacity="0.4" />
          <Coin id={id} cx={45} cy={42} r={13} />
        </>
      )}
    </svg>
  );
}
