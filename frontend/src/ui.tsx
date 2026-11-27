import type { ReactNode } from "react";
import { STATE_LABEL, stateTone, type Tone } from "./lib/format";
import type { RunState } from "./lib/types";

// Authored 24px line icons, one stroke weight (no emoji/unicode stand-ins).
const PATHS: Record<string, string> = {
  message: "M21 11a8 8 0 0 1-8 8H7l-5 3V11a9 9 0 0 1 9-9h1a9 9 0 0 1 9 9ZM7 8h9M7 12h6",
  overview: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  transactions: "M4 7h16M16 3l4 4-4 4M20 17H4M8 13l-4 4 4 4",
  search: "M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z",
  arrow: "M4 12h16M14 6l6 6-6 6",
  phone: "M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2ZM10 18h4",
  menu: "M4 6h16M4 12h16M4 18h16",
  settings: "M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1ZM16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
  check: "M20 6 9 17l-5-5",
  logout: "M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l-4-4 4-4M6 12h10",
  pause: "M8 5v14M16 5v14",
  checkCircle: "M22 11.1V12a10 10 0 1 1-5.9-9.1M22 4 12 14l-3-3",
  alert: "M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0ZM12 9v4M12 17h.01",
  x: "M18 6 6 18M6 6l12 12",
  xOctagon: "M7.9 2h8.2L22 7.9v8.2L16.1 22H7.9L2 16.1V7.9ZM15 9l-6 6M9 9l6 6",
  lock: "M5 11h14v10H5zM8 11V7a4 4 0 1 1 8 0v4",
  box: "M21 8 12 3 3 8v8l9 5 9-5ZM3 8l9 5 9-5M12 13v8",
  trash: "M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z",
  camera: "M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3ZM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z",
  upload: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12",
  download: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3",
  file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8ZM14 2v6h6M8 13h8M8 17h5",
  grid: "M3 3h18v18H3zM3 9h18M3 15h18M9 3v18M15 3v18",
  play: "m6 4 14 8-14 8Z",
  refresh: "M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5",
  code: "m16 18 6-6-6-6M8 6l-6 6 6 6",
  user: "M20 21a8 8 0 0 0-16 0M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z",
  clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20ZM12 6v6l4 2",
  terminal: "m4 17 6-6-6-6M12 19h8",
  flag: "M4 22V4a1 1 0 0 1 1-1h12l-2 4 2 4H5",
};

export function Icon({ name, title }: { name: keyof typeof PATHS | string; title?: string }) {
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden={title ? undefined : true} role={title ? "img" : undefined}>
      {title ? <title>{title}</title> : null}
      <path d={PATHS[name] ?? PATHS.file} />
    </svg>
  );
}

const TONE_ICON: Record<Tone, string> = { ok: "checkCircle", warn: "alert", bad: "xOctagon", busy: "", neutral: "clock" };

export function Pill({ tone, children, icon }: { tone: Tone; children: ReactNode; icon?: string }) {
  const ic = icon ?? TONE_ICON[tone];
  return (
    <span className={`pill ${tone}`}>
      {tone === "busy" && !icon ? <span className="dot-busy" aria-hidden /> : ic ? <Icon name={ic} /> : null}
      {children}
    </span>
  );
}

export function StatePill({ state }: { state: RunState }) {
  return <Pill tone={stateTone(state)}>{STATE_LABEL[state] ?? state}</Pill>;
}

export function Callout({ tone, title, children, icon }: { tone: "warn" | "bad" | "ok" | "info"; title?: string; children?: ReactNode; icon?: string }) {
  const ic = icon ?? { warn: "alert", bad: "xOctagon", ok: "checkCircle", info: "flag" }[tone];
  return (
    <div className={`callout ${tone}`} role={tone === "bad" ? "alert" : "status"}>
      <Icon name={ic} />
      <div className="stack" style={{ gap: 4 }}>
        {title ? <strong>{title}</strong> : null}
        {children}
      </div>
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const e = error as { code?: string; message?: string };
  return (
    <Callout tone="bad" title={e.message ?? "Something went wrong."}>
      {e.code ? <p className="small">Code: <code>{e.code}</code></p> : null}
    </Callout>
  );
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="stack" aria-busy="true" aria-label="Loading">
      {Array.from({ length: lines }, (_, i) => <div key={i} className="skeleton" style={{ width: `${90 - i * 14}%` }} />)}
    </div>
  );
}
