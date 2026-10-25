import { Link, Navigate, NavLink, Outlet } from 'react-router-dom';
import Footer from '../components/Footer.jsx';
import UserMenu from '../components/UserMenu.jsx';
import { currentSession, getClientSession } from '../api/client.js';
import { useLoad } from '../api/useLoad.js';

// Кабинет клиента — только после входа под тестовой учёткой клиента.
// Hero и белый лист рисует сама страница (components/Page.jsx).
export default function ClientLayout() {
  const { data: session } = useLoad(getClientSession, []);
  if (currentSession()?.role !== 'client') return <Navigate to="/login" replace />;

  const NAV = [
    { to: '/assistant', label: 'Подбор кредита' },
    { to: '/catalog', label: 'Каталог' },
    ...(session?.applicationId ? [{ to: `/applications/${session.applicationId}`, label: 'Моя заявка' }] : []),
  ];

  return (
    <div className="shell">
      <header className="app-header">
        <div className="app-header__inner">
          {/* Логотип не используем: цвет + фундамент закрывают узнаваемость по брендбуку */}
          <Link to="/" className="logo"><span className="fundament">Альфа Бизнес</span></Link>
          <nav className="nav">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} className="nav__link">{item.label}</NavLink>
            ))}
          </nav>
          <div className="app-header__aside">
            <Link to="/apply" className="header-btn">Новая заявка</Link>
            {session && <UserMenu name={session.name} role={session.company.type === 'ip' ? 'Индивидуальный предприниматель' : 'Юридическое лицо'} />}
          </div>
        </div>
      </header>
      <Outlet />
      <Footer />
    </div>
  );
}
