import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Avatar from './Avatar.jsx';
import { logout } from '../api/client.js';

// Аватар в шапке: по клику — имя, роль и «Выйти». Закрывается по Esc и клику мимо.
export default function UserMenu({ name, role }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return undefined;
    const onClick = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('mousedown', onClick); document.removeEventListener('keydown', onKey); };
  }, [open]);

  const signOut = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="user-menu" ref={ref}>
      <button type="button" className="user-chip" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        <Avatar name={name} />
        <span className="user-chip__name">{name}</span>
        <span className="user-chip__caret" aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="user-menu__popover" role="menu">
          <div className="user-menu__head">
            <b>{name}</b>
            <span className="muted small">{role}</span>
          </div>
          <button type="button" role="menuitem" className="user-menu__item" onClick={signOut}>Выйти</button>
        </div>
      )}
    </div>
  );
}
