# Normative data contracts

Contract revision: `ledgerflow.v1`. These definitions are implementation specifications. Examples are hypothetical, not recorded execution evidence. API routes are defined in [API_CONTRACT](API_CONTRACT.md); persistence is defined in [DATABASE](DATABASE.md).

## Shared conventions

* All objects reject unknown fields. Strings, booleans and integers are validated strictly; numeric strings never become integers automatically. Distinguish absent, null and zero.
* IDs are server-generated opaque strings with a type prefix (`wb_`, `ver_`, `map_`, `doc_`, `txn_`, `run_`, `plan_`, `att_`, `art_`, `val_`, `apr_`, `cmt_`, `evt_`). Maximum 80 ASCII letters/digits/underscore/hyphen. IDs confer no permission.
* SHA-256 fields contain exactly 64 lowercase hexadecimal characters. Hashes over files cover exact bytes. Hashes over contract objects use UTF-8 JSON with sorted ASCII property keys, compact separators, no insignificant whitespace, no floats, no Unicode normalization, and arrays in specified order. Exclude the object's own hash field when calculating it. The worker persists the exact canonical bytes used.
* Timestamps use RFC 3339 UTC with `Z`. Accounting dates use `YYYY-MM-DD` and the confirmed company period/timezone; date and timestamp are different types.
* Money is an integer number of minor units in API/DB. P0 supports `SEK`, exponent 2, nonnegative gross/net/tax amounts up to 10^12 per line. Unknown tax is null, never zero. A refund is a separate workflow, not a negative purchase.
* Account IDs are strings matching the confirmed chart, maximum 32 characters. Currency and payment context are explicit, not inferred from account numbering.
* Cell coordinates use uppercase A1 notation, row 1–1,048,576 and column A–XFD. Worksheet names are exact source strings, maximum 31 characters. No formula/range expression is accepted where a single cell is expected.
* Human explanations are plain text, maximum 2,000 characters. Source text never becomes HTML, shell input or a formula.

## Transaction: `TransactionV1`

| Field | Type / requirement |
|---|---|
| schema_version | Required literal `ledgerflow.transaction.v1` |
| transaction_id, document_id, tenant_id | Required server-owned IDs |
| revision | Required positive integer; extraction corrections create a new revision |
| document_sha256 | Required exact original image/document bytes hash |
| normalized_image_sha256 | Required hash of image actually sent to VSI |
| kind | Required `purchase_receipt` or `supplier_invoice` |
| merchant_name | Required nullable string, max 200 |
| supplier_reference | Required nullable string, max 100 |
| document_date | Required nullable accounting date |
| currency | Required nullable literal `SEK` in P0 |
| gross_minor, net_minor, tax_minor | Required nullable bounded integers |
| tax_lines | Required array of `TaxLineV1`, max 10; empty only when unresolved or confirmed tax-free |
| payment_status | Required `paid`, `unpaid`, `unknown` |
| payment_source | Required `company_bank`, `company_cash`, `employee_personal`, `unknown` |
| payment_account_id | Required nullable confirmed chart ID; human/policy supplied |
| category_account_id | Required nullable confirmed chart ID |
| tax_treatment | Required `configured_deductible`, `configured_nondeductible`, `tax_free`, `unknown` |
| policy_version | Required nullable confirmed policy ID/version string |
| evidence | Required array of `FieldEvidenceV1`, max 40 |
| unresolved_fields | Required array of unique field names, max 20 |
| confirmed_by, confirmed_at | Required nullable actor ID/timestamp |
| exact_duplicate_key | Required server-owned hash scoped to tenant + source bytes |
| semantic_duplicate_key | Required nullable server-owned hash scoped to workbook and normalized supplier/reference/date/currency/gross |

`TaxLineV1`: `base_minor` nullable bounded integer; `tax_minor` nullable bounded integer; `rate_basis_points` nullable integer 0–10,000; `source_evidence_ids` array of 1–5 evidence IDs. This is extracted evidence, not permission to deduct tax. Mixed-rate or unclear-tax cases enter review in P0.

`FieldEvidenceV1`: `evidence_id` string max 80; `field` permitted TransactionV1 field; `source` literal `receipt_image` or `human_confirmation`; `text` nullable string max 300; `bbox` nullable array of four integers `[x1,y1,x2,y2]` in normalized 0–1000 coordinates; `page` literal 1 in P0; `status` `observed`, `unreadable`, `confirmed`. A model's evidence quotation is a claim to review, not an independent ground-truth detector.

Admission: require date, currency, gross, tax treatment, category, payment status/source/account as applicable, and net/tax reconciliation. `net_minor + tax_minor = gross_minor` when both known. Software does not recompute a missing receipt tax from a model-guessed rate. Supplier invoice liability posting uses confirmed accounts payable and an explicit unpaid status. `employee_personal` is held unless a reimbursement liability account is explicitly configured.

## Accounting entry: `EntryV1`

Required fields: `entry_id` (max 80), `transaction_id`, `transaction_revision`, `accounting_date`, `currency`, `policy_version`, `lines` (2–12 `EntryLineV1` objects), `explanation`, and `source_evidence_ids` (1–20).

`EntryLineV1` has required `line_id` (max 80), `account_id`, `side` (`debit`/`credit`), `amount_minor` (integer 1–10^12), `purpose` (`expense`, `input_tax`, `payment`, `liability`, `other_confirmed`), and `evidence_ids` (1–10). A line has one side only. Zero lines are omitted. Accounts and purposes must be admitted by the confirmed policy. Sum of debit amounts equals sum of credit amounts exactly. P0 refuses entries with more than one currency.

Hypothetical entry:

```json
{
  "entry_id": "entry_demo_1",
  "transaction_id": "txn_demo_1",
  "transaction_revision": 1,
  "accounting_date": "2026-11-27",
  "currency": "SEK",
  "policy_version": "policy_demo_1",
  "lines": [
    {"line_id":"line_expense","account_id":"6110","side":"debit","amount_minor":10000,"purpose":"expense","evidence_ids":["e_total","e_category"]},
    {"line_id":"line_tax","account_id":"2640","side":"debit","amount_minor":2500,"purpose":"input_tax","evidence_ids":["e_tax","e_policy"]},
    {"line_id":"line_payment","account_id":"1940","side":"credit","amount_minor":12500,"purpose":"payment","evidence_ids":["e_total","e_payment"]}
  ],
  "explanation": "Confirmed company-bank purchase: SEK 100.00 supplies and SEK 25.00 configured deductible input tax; bank credit SEK 125.00.",
  "source_evidence_ids": ["e_total","e_tax","e_category","e_policy","e_payment"]
}
```

## Workbook mapping: `WorkbookMappingV1`

| Field | Type / requirement |
|---|---|
| schema_version | Literal `ledgerflow.mapping.v1` |
| mapping_id, workbook_id | Required IDs |
| mapping_version | Positive integer, monotonically increasing per workbook |
| source_sha256 | Original inspected bytes hash |
| layout_sha256 | Canonical compatibility-hash input defined in EXCEL_ENGINE |
| mapping_sha256 | Hash of canonical immutable mapping excluding this field |
| inspector_version, adapter_version | Required immutable component versions |
| status | `proposed`, `confirmed`, `invalidated` |
| currency, money_exponent, amount_unit | `SEK`, 2, `major_units` |
| date_system | `excel_1900` or `excel_1904` |
| layout | `t_accounts` or `journal` |
| sheets | Array 1–10: exact `name`, `sheet_id`, `part`, `state` (`visible`/`hidden`/`veryHidden`) |
| instructions | Array 0–20: `sheet`, `range`, `text_sha256`, bounded `text`, `evidence_id` |
| accounts | Array 1–200 `AccountMappingV1` |
| journal | Required nullable `JournalMappingV1`; null for T-accounts |
| forbidden_regions | Array 1–500: `sheet`, `range`, `reason` |
| formulas | Array 0–500: `sheet`, `cell`, exact `formula`, nullable `cached_value`, `role`, `precedent_ranges`, `evaluation_status` |
| opening_balances | Array 0–200: `account_id`, `side`, `reference_cell`, `amount_cell`, exact `amount_minor`, `sheet` |
| feature_manifest_sha256 | Package manifest hash |
| preservation_policy | Literal `ooxml_cell_spans_v1` or `simple_openpyxl_profile_v1` |
| policy_version | Nullable for proposed mapping; confirmed accounting policy revision required when confirmed |
| baseline_report_sha256 | Required report hash |
| baseline_acknowledgement | Nullable object `report_sha256`, `base_sha256`, `actor_id`, `acknowledged_at`, `reason`; cannot waive unsafe new changes |
| confirmed_by, confirmed_at | Nullable actor/time; required non-null when confirmed |

`AccountMappingV1` fields: `account_id`, `name`, `role` (`asset`, `liability`, `equity`, `income`, `expense`, `tax`, `unclassified`), `sheet`, `header_range`, `evidence_ids`, `debit` and `credit`. Each side has `reference_column`, `amount_column`, `first_row`, `last_row`, `reference_format` literal `bracketed_account_id`, and `candidate_ranges` array of exact pair ranges. For journal layouts `debit`/`credit` are null and the journal binding applies. Unclassified accounts cannot be used without policy confirmation.

`JournalMappingV1`: `sheet`, `header_row`, `first_data_row`, `last_data_row`, `columns` object with required nullable keys `date`, `transaction_id`, `account_id`, `description`, `debit`, `credit`, `amount`, `side`, `currency`; `amount_convention` `separate_debit_credit` or `amount_and_side`; nullable `table_name`, nullable `table_range`; `required_columns` array. Each non-null column is an Excel column label. P0 refuses a signed amount without an explicit side convention.

An execution slot reservation is **not stored in this static mapping**. It belongs to an admitted execution plan pinned to one source version.

## Plan and code: `ExecutionPlanV1`

Required: `schema_version`=`ledgerflow.plan.v1`, `plan_id`, `run_id`, `transaction_id`, `transaction_revision`, `base_version_id`, `base_sha256`, `mapping_id`, `mapping_version`, `mapping_sha256`, `policy_version`, `entry` (EntryV1), `operations` (1–100 `CellOperationV1`), `posting_allocations` (1–30 `PostingAllocationV1`), `allow_calcpr_change` boolean, `plan_sha256`, `created_at`.

`CellOperationV1`: `sheet`, `cell`, `before` (typed cell snapshot), `after` (typed scalar snapshot), `line_id`, `allocation_id`, `role` (`debit_reference`, `debit_amount`, `credit_reference`, `credit_amount`, `journal_date`, `journal_id`, `journal_account`, `journal_description`, `journal_amount`, `journal_side`, `journal_currency`). `before` must be the verified actual source cell; amount/reference writes normally require blank. The source style ID is part of before and is invariant.

`PostingAllocationV1`: `allocation_id`, `debit_line_id`, `credit_line_id`, `amount_minor` positive bounded integer; `debit_cells` and `credit_cells` arrays of exact sheet/cell pairs. Sum of allocated edges incident on each line equals that line's amount. For journal layouts allocations may omit contra cells but financial conservation still applies.

`GeneratedProgramV1`: `language` literal `python`, `code` string 1–32,768 bytes, `code_sha256`, `plan_sha256`, `model_id`, nullable `provider_request_id`, `prompt_version`, `generation_index` 1–2. Fixed execution paths are `/input/source.xlsx`, `/input/plan.json`, `/input/mapping.json`, `/input/main.py`, output `/work/candidate.xlsx`. Generated code cannot choose host paths or runtime policy.

The model-response envelope has `entry`, `proposed_operations`, `plan_explanation`, and `python_code`; the server converts this proposal into the canonical admitted plan. Server-owned IDs/hashes/roles are never trusted from model output.

## Typed cell and diff

`CellSnapshotV1`: required `type` (`blank`, `number`, `text`, `boolean`, `error`, `formula`); `value` nullable string or boolean; `formula` nullable exact string; `style_id` nullable nonnegative integer. Numeric snapshots use decimal **strings** to avoid JSON float loss. A blank has null value/formula. A formula has exact formula text and nullable cached value, labeled as cached.

`CellDiffV1`: `sheet`, `cell`, `before`, `after`, `account_id`, `side` nullable debit/credit, `amount_delta_minor` nullable integer, `line_id`, `allocation_id`, `reason`. Diff arrays sort by source sheet order, row, column. Each cell appears once. Metadata diffs are separate objects with `part`, `field`, `before`, `after`, `reason`; a `calcPr` change is not disguised as a cell change.

## Validation report: `ValidationReportV1`

Required fields: `schema_version`=`ledgerflow.validation.v1`, `validation_id`, `run_id`, `attempt_id`, `verifier_version`, `verifier_image_digest`, `verifier_report_sha256`, `host_attestation_sha256`, `base_sha256`, `candidate_sha256`, `plan_sha256`, `mapping_sha256`, `policy_version`, `report_sha256`, `result` (`pass`, `fail`, `review_required`), `checks`, `cell_diff`, `metadata_diff`, `account_deltas`, `baseline`, `limitations`, `created_at`.

* `checks`: array of named checks, each `check_id`, `status` (`pass`, `fail`, `not_performed`), `expected`/`observed` nullable bounded scalar/string, `detail` max 500. Mandatory IDs: `archive_safe`, `exact_write_set`, `source_preconditions`, `account_allocation`, `new_entry_balanced`, `non_target_cells_unchanged`, `formulas_unchanged`, `formula_postings_stable`, `features_preserved`, `no_new_active_content`, `artifact_hash_match`, `cleanup_confirmed`.
* `account_deltas`: per account/currency exact `debit_minor` and `credit_minor`, compared to plan.
* `baseline`: `debits_minor`, `credits_minor`, `difference_minor`, `evaluation_status` (`complete_supported`, `incomplete`), `acknowledgement_required` boolean, nullable `acknowledgement_sha256`. It includes warnings about pre-existing errors; it does not alter them.
* `limitations`: plain-text array, maximum 20 items, explicitly including native recalculation not performed when applicable.

No `not_performed` mandatory check can yield `pass`. Cleanup is a host-attested check merged into the final report only after all associated isolated jobs are destroyed. The verifier's mathematical report and host lifecycle attestation retain separate hashes in the report envelope.

## Execution event: `ExecutionEventV1`

Required: `schema_version`=`ledgerflow.event.v1`, `event_id`, `sequence` (positive monotonic tenant integer), `run_id` nullable for workbook-level events, `attempt_id` nullable, `event_type`, `state`, `occurred_at`, `message`, `data`.

Permitted `event_type`: `run.created`, `run.state_changed`, `extraction.completed`, `review.required`, `plan.admitted`, `code.generated`, `sandbox.created`, `sandbox.started`, `sandbox.log`, `sandbox.exited`, `sandbox.destroyed`, `validation.completed`, `retry.scheduled`, `approval.created`, `commit.completed`, `run.failed`, `run.cancelled`, `containment.observed`.

`data` is a discriminated object per type: state change has `from`/`to`/`reason_code`; log has `stream` (`stdout`/`stderr`), `text` max 4,096 bytes and `truncated` boolean; sandbox exit has `exit_code` nullable integer, `termination_reason`, `duration_ms`, `peak_memory_bytes` nullable; validation has `report_sha256`/`result`; commit has `commit_id`/`version_id`/`artifact_sha256`. Other event data uses only server-generated object IDs/hashes and bounded status details. No arbitrary model object is forwarded directly to clients.

## Approval and commit

`ApprovalRequestV1` requires `decision` (`approve`/`reject`), `base_version_id`, `base_sha256`, `candidate_sha256`, `plan_sha256`, `mapping_sha256`, `validation_report_sha256`, `policy_version`, optional `comment` max 500. Server fills `approval_id`, `actor_id`, `created_at`, `expires_at` (15 minutes after creation) and the hash of the approval tuple.

`CommitV1` includes `commit_id`, `approval_id`, `run_id`, `workbook_id`, `previous_version_id`, `version_id`, `artifact_sha256`, `transaction_id`, `transaction_revision`, `committed_by`, `committed_at`. One immutable commit is permitted per transaction; corrections after commit use an explicit reversal/adjustment workflow beyond P0.

## Size and compatibility budgets

Plan operations ≤100; entry lines ≤12; model output ≤64 KiB transport body and code ≤32 KiB; event data ≤8 KiB; one log chunk ≤4 KiB; complete validation report ≤1 MiB; API run list ≤100 items; source workbook ≤10 MiB compressed and ≤100 MiB decompressed. Limits are ceilings, not target payload sizes. Every violation is a named refusal, never silent truncation of financially relevant fields.
