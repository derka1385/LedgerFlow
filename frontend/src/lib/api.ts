// Typed client for docs/API_CONTRACT.md. Same-origin, cookie session + X-CSRF-Token,
// Idempotency-Key on every mutation, error envelope -> ApiError.
import type {
  ApiErrorBody, ApprovalRequest, BenchmarkKpis, DiffResponse, ExecutionEvent, RunListItem, RunSnapshot, Session, UploadTarget, WorkbookView,
} from "./types";

const BASE = "/api/v1";
let csrf: string | null = null;
let backendLabel: string | null = null;

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public retryable = false,
              public details: Record<string, unknown> = {}) {
    super(message);
  }
}

export const isMockBackend = () => backendLabel === "DEV-MOCK";
export const isLocalBackend = () => backendLabel === "LOCAL";

export function newIdempotencyKey(prefix = "lf"): string {
  return `${prefix}_${crypto.randomUUID().replace(/-/g, "")}`;
}

interface ReqOpts {
  body?: unknown;
  form?: FormData;
  idempotencyKey?: string;
}

export async function req<T>(method: string, path: string, opts: ReqOpts = {}): Promise<T> {
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  if (method !== "GET") {
    if (csrf) headers["X-CSRF-Token"] = csrf;
    headers["Idempotency-Key"] = opts.idempotencyKey ?? newIdempotencyKey();
  }
  let res: Response;
  try {
    res = await fetch(BASE + path, { method, headers, body, credentials: "same-origin" });
  } catch {
    throw new ApiError(0, "NETWORK", "No connection to the server. Check your network and try again.", true);
  }
  backendLabel = res.headers.get("X-LedgerFlow-Backend") ?? backendLabel;
  const text = await res.text();
  let data: unknown = {};
  try { data = text ? JSON.parse(text) : {}; }
  catch { throw new ApiError(res.status, "INVALID_RESPONSE", "The server returned an unreadable response. Try again or contact your infrastructure owner.", true); }
  if (!res.ok) {
    if (res.status === 401 && path !== "/auth/session") window.dispatchEvent(new Event("ledgerflow:unauthenticated"));
    const e = (data as ApiErrorBody).error;
    throw new ApiError(res.status, e?.code ?? `HTTP_${res.status}`, e?.message ?? res.statusText, e?.retryable ?? false, e?.details ?? {});
  }
  return data as T;
}

// --- auth
export async function signIn(invite_token: string): Promise<Session> {
  const s = await req<Session>("POST", "/auth/session", { body: { invite_token } });
  csrf = s.csrf_token;
  return s;
}
export async function currentSession(): Promise<Session | null> {
  try {
    const s = await req<Session>("GET", "/auth/session");
    csrf = s.csrf_token;
    return s;
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null;
    throw e;
  }
}
export const signOut = () => req("DELETE", "/auth/session").then(result => { csrf = null; return result; });
export const adoptSession = (s: Session) => { csrf = s.csrf_token; };

// --- workbooks
export function uploadWorkbook(file: File, displayName: string, key: string) {
  const form = new FormData();
  form.append("file", file);
  form.append("display_name", displayName.slice(0, 120));
  return req<{ workbook_id: string; version_id: string; sha256: string; status: string }>("POST", "/workbooks", { form, idempotencyKey: key });
}
export const listWorkbooks = () => req<{ items: WorkbookView[] }>("GET", "/workbooks");
export const getWorkbook = (id: string) => req<WorkbookView>("GET", `/workbooks/${id}`);
export const getInspection = (id: string) => req<Record<string, any>>("GET", `/workbooks/${id}/inspection`);
export const proposeMapping = (id: string, base_version_id: string, base_sha256: string) =>
  req<{ mapping_id: string }>("POST", `/workbooks/${id}/mapping-proposals`, { body: { base_version_id, base_sha256 } });
export const getMapping = (wid: string, mid: string) => req<Record<string, any>>("GET", `/workbooks/${wid}/mappings/${mid}`);
export const confirmMapping = (wid: string, mid: string, body: Record<string, unknown>) =>
  req<Record<string, any>>("POST", `/workbooks/${wid}/mappings/${mid}/confirm`, { body });
export const uploadTargets = () => req<{ items: UploadTarget[] }>("GET", "/upload-targets");
export const listVersions = (wid: string) => req<{ items: Record<string, any>[] }>("GET", `/workbooks/${wid}/versions`);

// --- documents and runs
export function uploadDocument(workbookId: string, file: Blob, filename: string, clientUploadId: string, progress?: (percent: number) => void, signal?: AbortSignal) {
  const form = new FormData();
  form.append("file", file, filename);
  form.append("client_upload_id", clientUploadId);
  if (progress) return new Promise<{ document_id: string; sha256: string; status: string }>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const abort = () => xhr.abort();
    xhr.open("POST", `${BASE}/workbooks/${encodeURIComponent(workbookId)}/documents`);
    if (csrf) xhr.setRequestHeader("X-CSRF-Token", csrf);
    xhr.setRequestHeader("Idempotency-Key", `upload_${clientUploadId}`);
    xhr.timeout = 120000;
    xhr.upload.onprogress = e => { if (e.lengthComputable) progress(Math.round(e.loaded / e.total * 100)); };
    xhr.onloadend = () => signal?.removeEventListener("abort", abort);
    xhr.onerror = () => reject(new ApiError(0, "NETWORK", "Upload interrupted. Retry to resume the same submission.", true));
    xhr.ontimeout = () => reject(new ApiError(0, "TIMEOUT", "Upload timed out. Retry the same submission.", true));
    xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
    xhr.onload = () => {
      try {
        const data = JSON.parse(xhr.responseText);
        backendLabel = xhr.getResponseHeader("X-LedgerFlow-Backend") ?? backendLabel;
        if (xhr.status >= 200 && xhr.status < 300) resolve(data);
        else { if (xhr.status === 401) window.dispatchEvent(new Event("ledgerflow:unauthenticated")); reject(new ApiError(xhr.status, data.error?.code ?? `HTTP_${xhr.status}`, data.error?.message ?? "Upload failed.", data.error?.retryable ?? false)); }
      } catch { reject(new ApiError(xhr.status, "INVALID_RESPONSE", "The server returned an unreadable upload response.", true)); }
    };
    if (signal?.aborted) { reject(new DOMException("Upload cancelled", "AbortError")); return; }
    signal?.addEventListener("abort", abort, { once: true });
    xhr.send(form);
  });
  // Same key on retry: the server returns the original document instead of a second upload.
  return req<{ document_id: string; sha256: string; status: string }>("POST", `/workbooks/${workbookId}/documents`,
    { form, idempotencyKey: `upload_${clientUploadId}` });
}
export const getDocument = (id: string) => req<{ document_id: string; status: string; image_url?: string }>("GET", `/documents/${encodeURIComponent(id)}`);
export function createRun(t: UploadTarget, document_id: string, client_request_id: string) {
  return req<{ run_id: string; state: string; events_url: string }>("POST", "/runs", {
    body: {
      workbook_id: t.workbook_id, document_id, expected_base_version_id: t.base_version_id, expected_base_sha256: t.base_sha256,
      mapping_id: t.mapping_id, mapping_version: t.mapping_version, client_request_id,
    },
    idempotencyKey: `run_${client_request_id}`,
  });
}
export const listRuns = (state?: string) => req<{ items: RunListItem[] }>("GET", `/runs${state ? `?state=${encodeURIComponent(state)}` : ""}`);
export const getRun = (id: string) => req<RunSnapshot>("GET", `/runs/${id}`);
export const getDiff = (id: string) => req<DiffResponse>("GET", `/runs/${id}/diff`);
export const approve = (id: string, body: ApprovalRequest, key: string) =>
  req<{ commit: RunSnapshot["commit"]; run: RunSnapshot }>("POST", `/runs/${id}/approval`, { body, idempotencyKey: key });
export const correctRun = (id: string, body: Record<string, unknown>) => req<Record<string, unknown>>("POST", `/runs/${id}/corrections`, { body });
export const resolveDuplicate = (id: string, body: Record<string, unknown>) => req<RunSnapshot>("POST", `/runs/${id}/duplicate-resolution`, { body });
export const cancelRun = (id: string, expected_run_revision: number) =>
  req<RunSnapshot>("POST", `/runs/${id}/cancel`, { body: { expected_run_revision, reason: "Cancelled from the review screen" } });
export const rerun = (id: string) => req<{ run_id: string }>("POST", `/runs/${id}/rerun`, { body: {} }); // extension
export const startContainmentTest = () => req<{ test_id: string }>("POST", "/containment-tests", { body: {} }); // extension
export const getContainmentTest = (id: string) => req<Record<string, any>>("GET", `/containment-tests/${id}`); // extension
// DEV MOCK only: sample files so demos and browser tests use the same upload path as a real photo.
export const listFixtures = () => req<{ workbooks: string[]; receipts: { case_id: string; title: string; file: string }[] }>("GET", "/dev/fixtures");
export async function fixtureFile(name: string): Promise<File> {
  const r = await fetch(`${BASE}/dev/fixtures/${encodeURIComponent(name)}`);
  if (!r.ok) throw new ApiError(r.status, "FIXTURE_UNAVAILABLE", "Sample file not available.");
  const blob = await r.blob();
  return new File([blob], name, { type: blob.type });
}
export const artifactUrl = (id: string) => `${BASE}/artifacts/${id}/download`;
export async function fetchText(artifactId: string): Promise<string> {
  const r = await fetch(artifactUrl(artifactId), { credentials: "same-origin" });
  if (!r.ok) throw new ApiError(r.status, "ARTIFACT_UNAVAILABLE", "Could not load this file.");
  return r.text();
}

// --- server-sent events: replay after the last sequence, dedupe, never the source of truth
export function subscribeRunEvents(runId: string, after: number, onEvent: (e: ExecutionEvent) => void,
                                   onStatus?: (s: "open" | "reconnecting") => void): () => void {
  const es = new EventSource(`${BASE}/runs/${runId}/events?after=${after}`, { withCredentials: true });
  const handler = (m: MessageEvent) => {
    try { onEvent(JSON.parse(m.data) as ExecutionEvent); } catch { /* ignore malformed */ }
  };
  const types = ["run.created", "run.state_changed", "extraction.completed", "review.required", "plan.admitted", "code.generated",
    "sandbox.created", "sandbox.started", "sandbox.log", "sandbox.exited", "sandbox.destroyed", "validation.completed",
    "retry.scheduled", "approval.created", "commit.completed", "run.failed", "run.cancelled", "containment.observed"];
  types.forEach((t) => es.addEventListener(t, handler as EventListener));
  es.onopen = () => onStatus?.("open");
  es.onerror = () => onStatus?.("reconnecting"); // EventSource retries with Last-Event-ID by itself
  return () => es.close();
}

/** Measured benchmark KPIs (DEV MOCK extension; 404 until benchmark/kpis.py has run). */
export const getBenchmarkKpis = () => req<BenchmarkKpis>("GET", "/benchmark/kpis");
