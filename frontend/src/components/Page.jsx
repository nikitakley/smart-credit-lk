// Страница кабинета, как на alfabank.ru: чёрный hero (заголовок, текст, действия, иллюстрация)
// и белый лист с контентом, который наезжает на hero скруглением.
// eyebrow — строка над заголовком (например, «← Очередь заявок»),
// extra — блок под подзаголовком (бейдж статуса, шаги, цифры).
export default function Page({ eyebrow, title, subtitle, extra, actions, art, children }) {
  return (
    <>
      <section className={`hero ${art ? '' : 'hero--plain'}`}>
        <div className="hero__inner">
          <div className="hero__text">
            {eyebrow && <div className="hero__eyebrow">{eyebrow}</div>}
            <h1 className="hero__title">{title}</h1>
            {subtitle && <p className="hero__subtitle">{subtitle}</p>}
            {extra && <div className="hero__extra">{extra}</div>}
            {actions && <div className="hero__actions">{actions}</div>}
          </div>
          {art && <div className="hero__art" aria-hidden="true">{art}</div>}
        </div>
      </section>
      <main className="sheet">
        <div className="page">{children}</div>
      </main>
    </>
  );
}
