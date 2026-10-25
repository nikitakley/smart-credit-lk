import { useCallback, useEffect, useState } from 'react';
import { CHANGE_EVENT } from './store.js';

// Загрузка данных; перезагружает при любом изменении демо-хранилища, в том числе из соседней вкладки.
// const { data, error, loading } = useLoad(() => getApplication(id), [id]);
export function useLoad(load, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(load, deps);

  useEffect(() => {
    let alive = true;
    const go = () => run().then(
      (data) => alive && setState({ data, error: null, loading: false }),
      (error) => alive && setState({ data: null, error, loading: false }),
    );
    go();
    window.addEventListener(CHANGE_EVENT, go);
    return () => { alive = false; window.removeEventListener(CHANGE_EVENT, go); };
  }, [run]);

  return state;
}
