import { Link, Navigate, NavLink, Outlet } from 'react-router-dom';
import Footer from '../components/Footer.jsx';
import UserMenu from '../components/UserMenu.jsx';
import { currentSession, getMe } from '../api/client.js';
import { useLoad } from '../api/useLoad.js';

const NAV = [
  { to: '/assistant', label: 'Подбор кредита' },
  { to: '/catalog', label: 'Каталог' },
  { to: '/applications', label: 'Мои заявки' },
];

// Кабинет клиента — только после входа под тестовой учёткой клиента.
// Hero и белый лист рисует сама страница (components/Page.jsx).
export default function ClientLayout() {
  const { data: me } = useLoad(getMe, []);
  const session = currentSession();
  if (session?.role !== 'client') return <Navigate to="/login" replace />;

  const name = me?.company?.name ?? session.name;
  const role = me?.company?.type === 'ip' ? 'Индивидуальный предприниматель' : 'Юридическое лицо';

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
            <UserMenu name={name} role={role} />
          </div>
        </div>
      </header>
      <Outlet />
      <Footer />
    </div>
  );
}
