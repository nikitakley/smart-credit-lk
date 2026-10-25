import Button from '../../components/Button.jsx';
import Page from '../../components/Page.jsx';
import ProductFacts from '../../components/ProductFacts.jsx';
import ProductIcon from '../../components/ProductIcon.jsx';
import ArtGrowth from '../../components/art/ArtGrowth.jsx';
import { getProducts } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';

export default function Catalog() {
  const { data: products } = useLoad(getProducts, []);

  return (
    <Page
      title="Кредиты для бизнеса"
      subtitle="На оборотные средства, развитие и кассовые разрывы. Не знаете, что выбрать, — помощник подберёт за четыре вопроса."
      actions={<Button to="/assistant" variant="ondark" size="l">Подобрать с помощником</Button>}
      art={<ArtGrowth />}
    >
      <section className="section">
        <h2 className="section-title">Продукты</h2>
        {/* Список как на alfabank.ru: серые строки, условия справа */}
        <ul className="product-list">
          {(products ?? []).map((p) => (
            <li key={p.id} className="product-row">
              <ProductIcon productId={p.id} />
              <div className="product-row__main">
                <h3>{p.name}</h3>
                <p className="muted small m0">{p.note}</p>
              </div>
              <ProductFacts product={p} />
              <Button to={`/apply?product=${p.id}`} size="s">Оформить</Button>
            </li>
          ))}
        </ul>
        {!products && <p className="muted">Загружаем продукты…</p>}
        <p className="muted small" style={{ marginTop: 'var(--space-4)' }}>Условия — демо-данные до подключения каталога банка.</p>
      </section>
    </Page>
  );
}
