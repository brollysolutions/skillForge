import { useCallback, useEffect, useState } from 'react';
import { api, errorText } from '../api/client';
export function useApi(path) {
  const [data, setData] = useState(null), [loading, setLoading] = useState(true), [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion(v => v + 1), []);
  useEffect(() => {
    if (!path) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true); setError('');
    api.get(path, { signal: controller.signal }).then(r => setData(r.data)).catch(e => {
      if (e.code !== 'ERR_CANCELED') setError(errorText(e));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [path, version]);
  return { data, loading, error, reload, setData };
}
