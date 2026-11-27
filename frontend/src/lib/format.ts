import type { ApprovalRequest, DiffResponse, ExecutionEvent, RunState } from "./types";

/** Integer öre -> "1,250.00". Never uses floating point. */
export function money(minor: number | null | undefined): string {
  if (minor === null || minor === undefined) return "—";
  const neg = minor < 0;
  const abs = Math.abs(minor);
  const major = Math.floor(abs / 100).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${neg ? "−" : ""}${major}.${String(abs % 100).padStart(2, "0")}`;
}

/** "1 250,00" / "1250.5" / "1,250.00" -> 125000 öre, or null if not an exact amount. */
export function parseMoney(input: string): number | null {
  let s = input.trim().replace(/\s| /g, "").replace(/kr|sek/gi, "");
  if (!s) return null;
  // "1,250" or "12.345" is ambiguous (thousands vs decimals): refuse rather than guess.
  if (/^\d{1,3}[.,]\d{3}$/.test(s)) return null;
  if (/^\d{1,3}(,\d{3})+(\.\d{1,2})?$/.test(s)) s = s.replace(/,/g, "");
  else if (/^\d{1,3}(\.\d{3})+(,\d{1,2})?$/.test(s)) s = s.replace(/\./g, "").replace(",", ".");
  else s = s.replace(",", ".");
  const m = /^(\d+)(?:\.(\d{1,2}))?$/.exec(s);
  if (!m) return null;
  const minor = Number(m[1]) * 100 + Number((m[2] ?? "0").padEnd(2, "0"));
  return Number.isSafeInteger(minor) && minor <= 1e12 ? minor : null;
}

/** RFC 3339 UTC -> local "2026-11-27 00:42:20" (sv-SE gives ISO-like order). */
export function localTime(iso: string | null | undefined, timeOnly = false): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const s = d.toLocaleString("sv-SE", { hour12: false });
  return timeOnly ? s.slice(11) : s;
}

export const shortHash = (h: string | null | undefined) => (h ? `${h.slice(0, 4)}…${h.slice(-4)}` : "—");

export const STATE_LABEL: Record<RunState, string> = {
  QUEUED: "Queued", EXTRACTING: "Reading document", NEEDS_REVIEW: "Needs your answer", DUPLICATE_REVIEW: "Possible duplicate",
  PLANNING: "Deciding the entry", GENERATING_CODE: "Writing the program", SANDBOX_STARTING: "Starting sandbox",
  EXECUTING: "Running in sandbox", VERIFYING: "Verifying", RETRY_PENDING: "Retrying", CLEANUP_PENDING: "Cleaning up",
  AWAITING_APPROVAL: "Ready to approve", COMMITTING: "Committing", COMMITTED: "Committed", REJECTED: "Rejected",
  FAILED: "Failed", CANCELLED: "Cancelled", EXPIRED: "Expired", STALE_BASE: "Out of date",
};

export type Tone = "ok" | "warn" | "bad" | "busy" | "neutral";
export function stateTone(s: RunState): Tone {
  if (s === "COMMITTED" || s === "AWAITING_APPROVAL") return "ok";
  if (s === "NEEDS_REVIEW" || s === "DUPLICATE_REVIEW" || s === "STALE_BASE" || s === "EXPIRED") return "warn";
  if (s === "FAILED" || s === "REJECTED" || s === "CANCELLED") return "bad";
  return "busy";
}
export const isTerminal = (s: RunState) =>
  ["COMMITTED", "REJECTED", "FAILED", "CANCELLED", "EXPIRED", "STALE_BASE"].includes(s);

/** Merge SSE events by sequence: replays and reconnects never duplicate a line. */
export function mergeEvents(prev: ExecutionEvent[], incoming: ExecutionEvent[]): ExecutionEvent[] {
  const seen = new Set(prev.map((e) => e.sequence));
  const add = incoming.filter((e) => !seen.has(e.sequence));
  if (!add.length) return prev;
  return [...prev, ...add].sort((a, b) => a.sequence - b.sequence);
}

/** The exact hash tuple the reviewer saw (ApprovalRequestV1). Built only from the server's diff response. */
export function approvalRequest(diff: DiffResponse, decision: "approve" | "reject", comment?: string): ApprovalRequest {
  return {
    decision,
    base_version_id: diff.base_version_id,
    base_sha256: diff.base_sha256,
    candidate_sha256: diff.candidate_sha256,
    plan_sha256: diff.plan_sha256,
    mapping_sha256: diff.mapping_sha256,
    validation_report_sha256: diff.validation.report_sha256,
    policy_version: diff.policy_version,
    ...(comment ? { comment: comment.slice(0, 500) } : {}),
  };
}

export const CHECK_LABEL: Record<string, string> = {
  archive_safe: "File is a safe, readable workbook",
  exact_write_set: "Exactly the planned cells changed",
  source_preconditions: "Targets were empty, inside mapped slots",
  account_allocation: "Postings land on the right accounts, mirrored",
  new_entry_balanced: "New entry balances (debit = credit)",
  non_target_cells_unchanged: "No other cell changed",
  formulas_unchanged: "Formulas untouched",
  formula_postings_stable: "No formula reads a written cell",
  features_preserved: "Every other file part byte-identical",
  no_new_active_content: "No macros or external links added",
  artifact_hash_match: "Hash recorded for approval",
  cleanup_confirmed: "Sandbox destroyed",
  "V-BAL-01": "Debits equal credits",
  "V-AMT-01": "Amounts are exact öre within bounds",
  "V-SEM-06": "No account on both sides",
  "V-SEM-01": "Each line on the right side for its purpose",
  "V-EXT-01": "Every line cites document evidence",
  "V-SEM-AMT": "Credit total equals the document total",
  "V-SEM-02": "VAT split matches the printed VAT",
  "V-SEM-03": "Payment status matches the accounts used",
  "V-SEM-04": "Allowed expense accounts only",
};

export const ACCOUNT_OPTIONS: [string, string][] = [
  ["6110", "Office supplies"], ["5420", "Software"], ["6540", "IT services"], ["6210", "Telecommunications"],
  ["6570", "Banking costs"], ["6810", "Travel tickets"], ["4010", "Purchases of goods"], ["5010", "Rent for premises"],
  ["5170", "Repairs and maintenance"],
];
