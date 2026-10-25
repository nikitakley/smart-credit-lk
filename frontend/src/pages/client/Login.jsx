import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Avatar from '../../components/Avatar.jsx';
import Card from '../../components/Card.jsx';
import ArtGrowth from '../../components/art/ArtGrowth.jsx';
import { getTestAccounts, login } from '../../api/client.js';
import { useLoad } from '../../api/useLoad.js';

// Вход по тестовым учётным записям. Клиенты — действующие клиенты банка, регистрации нет (FAQ п. 3).
// В промышленной версии — вход через Альфа-ID / ДБО, кабинет открывается уже авторизованным.
export default function Login() {
  const { data: accounts } = useLoad(getTestAccounts, []);
  const [busy, setBusy] = useState(null);
  const navigate = useNavigate();

  const enter = async (acc) => {
    setBusy(acc.id);
    const session = await login(acc.id);
    navigate(session.role === 'analyst' ? '/analyst' : '/assistant', { replace: true });
  };

  return (
    <div className="auth">
      <div className="auth__inner">
        <div className="auth__text">
          <Link to="/" className="logo"><span className="fundament">Альфа Бизнес</span></Link>
          <h1 className="hero__title">Кредитный кабинет для бизнеса</h1>
          <p className="hero__subtitle">Подбор продукта, заявка, решение банка с объяснением, подписание и выдача — в одном месте.</p>
          <div className="auth__art" aria-hidden="true"><ArtGrowth /></div>
        </div>

        <Card className="stack auth__card">
          <h2>Вход</h2>
          <p className="muted m0">Выберите тестовую учётную запись. Клиенты — действующие клиенты банка.</p>
          <div className="accounts">
            {(accounts ?? []).map((a) => (
              <button key={a.id} type="button" className="account" disabled={!!busy} onClick={() => enter(a)}>
                <Avatar name={a.name} light />
                <span className="account__text">
                  <b>{a.name}</b>
                  <span className="small muted">{a.role === 'analyst' ? 'Сотрудник банка' : `ИНН ${a.inn}`} · {a.hint}</span>
                </span>
                <span className="account__arrow" aria-hidden="true">{busy === a.id ? '…' : '→'}</span>
              </button>
            ))}
          </div>
          <p className="muted small m0">
            Пароль не нужен: это демо-вход. В рабочей версии клиент входит через Альфа-ID или интернет-банк и сразу попадает в кабинет своей компании.
          </p>
        </Card>
      </div>
    </div>
  );
}
