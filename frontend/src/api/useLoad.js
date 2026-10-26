import { useCallback, useEffect, useState } from 'react';
import { CHANGE_EVENT } from './http.js';

/**
 * Загрузка данных с перезапросом:
 * — после любого изменяющего запроса в этой вкладке (событие CHANGE_EVENT);
 * — по таймеру, если передан pollMs: так клиент видит решение аналитика из соседней вкладки.
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
    const go = () => run().then(
      (data) => alive && setState({ data, error: null, loading: false }),
      (error) => alive && setState((prev) => (prev.data ? prev : { data: null, error, loading: false })),
    );
    go();
    window.addEventListener(CHANGE_EVENT, go);
    const timer = pollMs ? setInterval(() => { if (document.visibilityState === 'visible') go(); }, pollMs) : null;
    return () => {
      alive = false;
      window.removeEventListener(CHANGE_EVENT, go);
      if (timer) clearInterval(timer);
    };
  }, [run, pollMs]);

  const mutate = useCallback((data) => setState({ data, error: null, loading: false }), []);
  return { ...state, mutate };
}
