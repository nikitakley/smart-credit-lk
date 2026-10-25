import { Link } from 'react-router-dom';

/**
 * variant: primary (тёмная, по умолчанию) | accent (красная, ОДНА на экран)
 *          | secondary (серая) | ondark (полупрозрачная — на чёрном hero и в шапке)
 * size: m (48px, по умолчанию) | s (40px — действия внутри карточек) | l (56px — hero)
 * to — если передан, рендерится ссылкой роутера с видом кнопки.
 */
export default function Button({ variant = 'primary', size = 'm', to, type = 'button', className = '', ...props }) {
  const sizeClass = size === 'm' ? '' : `btn--${size}`;
  const cls = ['btn', `btn-${variant}`, sizeClass, className].filter(Boolean).join(' ');
  if (to) return <Link to={to} className={cls} {...props} />;
  return <button type={type} className={cls} {...props} />;
}
