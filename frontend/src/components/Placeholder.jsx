// Временная рамка «что будет на этом месте» — убирается по мере вёрстки
export default function Placeholder({ title, items = [], children }) {
  return (
    <div className="placeholder">
      {title && <p className="placeholder__title">{title}</p>}
      {items.length > 0 && <ul>{items.map((it) => <li key={it}>{it}</li>)}</ul>}
      {children}
    </div>
  );
}
