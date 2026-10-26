import { useCallback, useEffect, useRef, useState } from 'react';
import { CHANGE_EVENT } from './http.js';
import { applicationPollMs } from '../config/statuses.js';

/**
 * Загрузка данных с перезапросом:
 * — после любого изменяющего запроса в этой вкладке (событие CHANGE_EVENT);
 * — по таймеру pollMs: число или функция (data) => мс | null (null — не опрашивать).
 *   Опрос идёт только на видимой вкладке и останавливается при уходе со страницы.
 * При ошибке повторной загрузки уже показанные данные не пропадают.
 * mutate(data) — подставить данные из ответа действия (например, обновлённую карточку), не дожидаясь перезапроса.
 * const { data, error, loading, mutate } = useLoad(() => getApplication(id), [id], { pollMs: 10000 });
 */
export function useLoad(load, deps, { pollMs } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(load, deps);

  useEffect(() => {
    let alive = true;
    let timer = null;
    let latest = null;

    const schedule = () => {
      clearTimeout(timer);
      const ms = typeof pollMs === 'function' ? pollMs(latest) : pollMs;
      if (alive && ms) timer = setTimeout(tick, ms);
    };
    const go = () => run().then(
      (data) => {
        if (!alive) return;
        latest = data;
        setState({ data, error: null, loading: false });
        schedule();
      },
      (error) => {
        if (!alive) return;
        setState((prev) => (prev.data ? prev : { data: null, error, loading: false }));
        schedule();
      },
    );
    // На скрытой вкладке не запрашиваем — только переносим проверку
    const tick = () => (document.visibilityState === 'visible' ? go() : schedule());

    go();
    window.addEventListener(CHANGE_EVENT, go);
    return () => {
      alive = false;
      clearTimeout(timer);
      window.removeEventListener(CHANGE_EVENT, go);
    };
  }, [run, pollMs]);

  const mutate = useCallback((data) => setState({ data, error: null, loading: false }), []);
  return { ...state, mutate };
}

/**
 * Заявка с опросом по статусу (интервалы — applicationPollMs в config/statuses.js).
 * Время в статусе считаем с момента, когда страница впервые увидела этот статус.
 */
export function useApplication(load, deps) {
  const seen = useRef({ status: null, since: 0 });
  const pollMs = useCallback((app) => {
    if (!app) return 10000; // заявка ещё не загрузилась (например, бэкенд недоступен) — пробуем снова
    if (app.status !== seen.current.status) seen.current = { status: app.status, since: Date.now() };
    return applicationPollMs(app.status, Date.now() - seen.current.since);
  }, []);
  return useLoad(load, deps, { pollMs });
}
