import { useEffect, useRef, useState } from "react";

// One request at a time; stop while hidden, refresh immediately on return.
export function usePolling<T>(load: () => Promise<T>, interval = 4000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const fn = useRef(load); fn.current = load;
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let disposed = false, pending = false;
    const refresh = async () => {
      if (pending || document.hidden) return;
      pending = true;
      try { const next = await fn.current(); if (!disposed) { setData(next); setError(null); } }
      catch (e) { if (!disposed) setError(e); }
      finally { pending = false; }
    };
    void refresh();
    const timer = window.setInterval(refresh, interval);
    document.addEventListener("visibilitychange", refresh);
    window.addEventListener("online", refresh);
    return () => { disposed = true; clearInterval(timer); document.removeEventListener("visibilitychange", refresh); window.removeEventListener("online", refresh); };
  }, [interval, revision]);
  return { data, error, refresh: () => setRevision(n => n + 1) };
}
