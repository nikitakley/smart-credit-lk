import Button from '../components/Button.jsx';
import Footer from '../components/Footer.jsx';
import Page from '../components/Page.jsx';

export default function NotFound() {
  return (
    <div className="shell">
      <Page
        title="Страница не найдена"
        subtitle="Возможно, ссылка устарела. Начните с подбора кредита."
        actions={<Button to="/" variant="ondark" size="l">На главную</Button>}
      >
        <p className="muted m0">Код ошибки: 404</p>
      </Page>
      <Footer />
    </div>
  );
}
