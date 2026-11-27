// Contract types from docs/API_CONTRACT.md + docs/DATA_SCHEMAS.md (ledgerflow.v1).
// Fields marked "extension" are proposed additions the DEV MOCK returns; see FRONTEND_HANDOFF.md.

export type Role = "employee" | "accountant" | "owner";

export interface Session {
  user_id: string;
  role: Role;
  tenant_id: string;
  csrf_token: string;
  expires_at: string;
  display_name?: string; // extension
  backend?: string; // extension: "DEV-MOCK" from the mock
  inference?: "vultr" | "mock" | "unavailable";
}

export type RunState =
  | "QUEUED" | "EXTRACTING" | "NEEDS_REVIEW" | "DUPLICATE_REVIEW" | "PLANNING" | "GENERATING_CODE"
  | "SANDBOX_STARTING" | "EXECUTING" | "VERIFYING" | "RETRY_PENDING" | "CLEANUP_PENDING" | "AWAITING_APPROVAL"
  | "COMMITTING" | "COMMITTED" | "REJECTED" | "FAILED" | "CANCELLED" | "EXPIRED" | "STALE_BASE";

export interface Evidence {
  evidence_id: string;
  field: string;
  source: "receipt_image" | "human_confirmation";
  text: string | null;
  status: "observed" | "unreadable" | "confirmed";
}

export interface TaxLine {
  base_minor: number | null;
  tax_minor: number | null;
  rate_basis_points: number | null;
}

export interface Transaction {
  transaction_id: string;
  revision: number;
  kind: "purchase_receipt" | "supplier_invoice";
  merchant_name: string | null;
  supplier_reference: string | null;
  supplier_org_no?: string | null; // extension (needed for VAT deduction; not in TransactionV1)
  document_date: string | null;
  currency: "SEK" | null;
  gross_minor: number | null;
  net_minor: number | null;
  tax_minor: number | null;
  tax_lines: TaxLine[];
  payment_status: "paid" | "unpaid" | "unknown";
  payment_source: "company_bank" | "company_cash" | "employee_personal" | "unknown";
  category_account_id: string | null;
  tax_treatment: "configured_deductible" | "configured_nondeductible" | "tax_free" | "unknown";
  evidence: Evidence[];
  unresolved_fields: string[];
}

export interface EntryLine {
  line_id: string;
  account_id: string;
  side: "debit" | "credit";
  amount_minor: number;
  purpose: string;
  evidence_ids: string[];
}

export interface Entry {
  entry_id: string;
  accounting_date: string;
  currency: string;
  policy_version: string;
  lines: EntryLine[];
  explanation: string;
}

export interface ReviewItem {
  code: string;
  field: string | null;
  message: string;
  detail: string;
}

export interface Commit {
  commit_id: string;
  version_id: string;
  previous_version_id: string;
  artifact_sha256: string;
  artifact_id?: string; // extension: download id
  audit_artifact_id?: string; // extension
  committed_by: string;
  committed_at: string;
}

export interface RunSnapshot {
  run_id: string;
  revision: number;
  workbook_id: string;
  document_id: string;
  state: RunState;
  state_reason: string;
  base_version_id: string;
  mapping_version: number;
  transaction_revision: number | null;
  attempt_count: number;
  last_event_sequence: number;
  transaction: Transaction | null;
  entry: Entry | null;
  plan_sha256: string | null;
  validation_summary: { result: string; report_sha256: string; checks_passed: number; checks_total: number; runtime?: string } | null;
  candidate_artifact_id: string | null;
  candidate_sha256: string | null;
  commit: Commit | null;
  created_at: string;
  updated_at: string;
  // extensions
  review_items?: ReviewItem[];
  advisories?: string[];
  security_flags?: string[];
  duplicate_of?: string | null;
  code_artifact_id?: string | null;
  mock_labels?: string[];
}

export interface RunListItem {
  run_id: string;
  workbook_id?: string;
  capture_origin?: string | null;
  expense_category?: string | null;
  state: RunState;
  state_reason: string;
  merchant_name: string | null;
  gross_minor: number | null;
  document_date: string | null;
  kind: string | null;
  validation_summary: RunSnapshot["validation_summary"];
  created_at: string;
  updated_at: string;
}

export interface ExecutionEvent {
  schema_version: "ledgerflow.event.v1";
  event_id: string;
  sequence: number;
  run_id: string | null;
  attempt_id: string | null;
  event_type: string;
  state: RunState | null;
  occurred_at: string;
  message: string;
  data: Record<string, unknown>;
}

export interface CellSnapshot {
  type: "blank" | "number" | "text" | "boolean" | "error" | "formula";
  value: string | boolean | null;
  formula: string | null;
  style_id: number | null;
}

export interface CellDiff {
  sheet: string;
  cell: string;
  before: CellSnapshot;
  after: CellSnapshot;
  account_id: string | null;
  side: "debit" | "credit" | null;
  amount_delta_minor: number | null;
  line_id: string;
  allocation_id: string;
  reason: string;
}

export interface Check {
  check_id: string;
  status: "pass" | "fail" | "not_performed";
  expected: string | null;
  observed: string | null;
  detail: string;
}

export interface ValidationReport {
  result: "pass" | "fail" | "review_required";
  report_sha256: string;
  verifier_version: string;
  checks: Check[];
  cell_diff: CellDiff[];
  account_deltas: { account_id: string; debit_minor: number; credit_minor: number }[];
  baseline: { debits_minor: number; credits_minor: number; difference_minor: number; acknowledgement_required: boolean } | null;
  limitations: string[];
  runtime?: string; // extension
}

export interface DiffResponse {
  validation: ValidationReport;
  base_version_id: string;
  base_sha256: string;
  candidate_sha256: string;
  plan_sha256: string;
  mapping_sha256: string;
  policy_version: string;
}

export interface ApprovalRequest {
  decision: "approve" | "reject";
  base_version_id: string;
  base_sha256: string;
  candidate_sha256: string;
  plan_sha256: string;
  mapping_sha256: string;
  validation_report_sha256: string;
  policy_version: string;
  comment?: string;
}

export interface WorkbookView {
  workbook_id: string;
  display_name: string;
  status: "inspecting" | "inspected" | "ready" | "unsupported";
  current_version_id: string;
  current_sha256: string;
  version_count: number;
  mapping: { mapping_id: string; mapping_version: number; mapping_sha256: string; status: string } | null;
  compatibility: Record<string, unknown> | null;
  baseline_summary: {
    debits_minor: number; credits_minor: number; difference_minor: number;
    opening_debits_minor: number; opening_credits_minor: number; acknowledgement_required: boolean;
  } | null;
}

export interface UploadTarget {
  workbook_id: string;
  display_name: string;
  base_version_id: string;
  base_sha256: string;
  mapping_id: string;
  mapping_version: number;
}

export interface ApiErrorBody {
  error: { code: string; message: string; retryable: boolean; request_id: string; details: Record<string, unknown> };
}

// ---- benchmark KPIs (GET /api/v1/benchmark/kpis, schema ledgerflow.kpis.v1; DEV MOCK extension)
export type KpiSourceKind = "deterministic" | "sandbox" | "scripted_model" | "mock" | "live_vultr" | "not_run";
export interface KpiFraction { value: number | null; numerator: number; denominator: number; display: string }
export interface Kpi {
  id: string; label: string; value: number | null; display: string; unit: string; source_kind: KpiSourceKind;
  suite_id: string; limitation: string; numerator?: number; denominator?: number;
  comparison?: { label: string; display: string };
}
export interface LiveModelKpis {
  config: string; model_id: string; reasoning_effort: string; booked_right: KpiFraction; critical_field_accuracy_pct: number | null;
  invented_critical_facts: number; injection_flagged: string; code_first_try: KpiFraction; code_after_retry: KpiFraction;
  read_latency_p50_s: number | null; code_latency_p50_s: number | null; cost_usd_per_receipt: number | null;
  previous_run_booked_right: string | null; recommended: boolean;
}
export interface BenchmarkKpis {
  schema_version: "ledgerflow.kpis.v1"; generated_at: string;
  source: { file: string; sha256: string; benchmark_generated_at: string; e2e_file: string | null };
  source_kinds: Record<string, string>;
  primary_model: { config: string; model_id: string; reasoning_effort: string; chosen_by: string; codegen_prompt: string;
                   budget_alternative: string | null } | null;
  kpis: Kpi[]; live_models: LiveModelKpis[]; e2e: Record<string, unknown> | null; limitations: string[];
}
