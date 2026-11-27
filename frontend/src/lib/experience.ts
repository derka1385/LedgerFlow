import type { ExecutionEvent, RunState } from "./types";

export const ACTIVE_STATES: RunState[] = ["QUEUED", "EXTRACTING", "PLANNING", "GENERATING_CODE", "SANDBOX_STARTING", "EXECUTING", "VERIFYING", "RETRY_PENDING", "CLEANUP_PENDING", "COMMITTING"];
export const QUESTION_STATES: RunState[] = ["NEEDS_REVIEW", "DUPLICATE_REVIEW", "STALE_BASE"];
export const ATTENTION_STATES: RunState[] = [...QUESTION_STATES, "FAILED", "EXPIRED"];

export function employeeStatus(state: RunState): string {
  if (state === "QUEUED") return "Uploaded";
  if (state === "NEEDS_REVIEW") return "Additional information needed";
  if (state === "DUPLICATE_REVIEW") return "Finance is checking a possible duplicate";
  if (state === "AWAITING_APPROVAL") return "Awaiting approval";
  if (state === "COMMITTED") return "Booked";
  if (state === "REJECTED") return "Rejected";
  if (state === "CANCELLED") return "Cancelled";
  if (state === "FAILED" || state === "EXPIRED" || state === "STALE_BASE") return "Finance attention needed";
  return "Processing";
}

// Count only values actually reported by the server. Missing telemetry stays missing.
export function executionMetrics(events: ExecutionEvent[]) {
  const unique = [...new Map(events.map(e => [e.sequence, e])).values()];
  const durations = unique.filter(e => e.event_type === "sandbox.exited").map(e => e.data.duration_ms).filter((x): x is number => typeof x === "number" && Number.isFinite(x) && x >= 0);
  const usages = unique.map(e => e.data.usage).filter((x): x is Record<string, unknown> => !!x && typeof x === "object");
  const tokens = usages.map(u => u.total_tokens ?? (typeof u.prompt_tokens === "number" && typeof u.completion_tokens === "number" ? u.prompt_tokens + u.completion_tokens : undefined)).filter((x): x is number => typeof x === "number" && Number.isFinite(x) && x >= 0);
  return { durationMs: durations.length ? durations.reduce((a, b) => a + b, 0) : null, tokens: tokens.length ? tokens.reduce((a, b) => a + b, 0) : null };
}

export function captureLink(origin: string, workbookId?: string): string {
  const url = new URL(origin);
  if (url.protocol !== "https:" && !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) throw new Error("Use the public HTTPS application for iPhone capture.");
  url.pathname = "/"; url.search = "";
  url.hash = `/capture${workbookId ? `?workbook=${encodeURIComponent(workbookId)}` : ""}`;
  return url.href;
}

export function pairingLink(origin: string, token: string): string {
  const url = new URL(captureLink(origin));
  if (url.protocol !== "https:") throw new Error("Secure pairing requires the public HTTPS application.");
  url.hash = `/pair/${encodeURIComponent(token)}`; // fragment is never sent in the HTTP request
  return url.href;
}

export function safeDocumentUrl(value: string): string | null {
  try { const u = new URL(value, location.origin); return u.origin === location.origin && u.pathname.startsWith("/api/v1/") ? u.href : null; } catch { return null; }
}
