import { Link, Navigate, NavLink, Outlet } from 'react-router-dom';
import Footer from '../components/Footer.jsx';
import UserMenu from '../components/UserMenu.jsx';
import { currentSession } from '../api/client.js';

// Кабинет аналитика — только после входа под тестовой учёткой сотрудника банка.
// Hero и белый лист рисует сама страница (components/Page.jsx).
export default function AnalystLayout() {
  const session = currentSession();
  if (session?.role !== 'analyst') return <Navigate to="/login" replace />;

  return (
    <div className="shell">
      <header className="app-header">
        <div className="app-header__inner">
          <Link to="/analyst" className="logo">
            <span className="fundament">Альфа Бизнес</span>
            <span className="logo__role">Аналитик</span>
          </Link>
          <nav className="nav">
            <NavLink to="/analyst" end className="nav__link">Очередь заявок</NavLink>
          </nav>
          <div className="app-header__aside">
            <UserMenu name={session.name} role="Сотрудник банка" />
          </div>
        </div>
      </header>
      <Outlet />
      <Footer />
    </div>
  );
}
