import Button from './Button.jsx';
import Page from './Page.jsx';

const TITLE = { 403: 'Недостаточно прав', 404: 'Не найдено' };

// Экран вместо страницы, если её данные не загрузились: текст ошибки с сервера и путь назад к списку
export default function LoadError({ error, eyebrow, backTo, backLabel }) {
  return (
    <Page
      eyebrow={eyebrow}
      title={TITLE[error.status] ?? 'Не удалось загрузить'}
      subtitle={error.message}
      actions={<Button to={backTo} variant="ondark" size="l">{backLabel}</Button>}
    />
  );
}
