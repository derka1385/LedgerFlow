# Adaptive Excel engine

## Supported surface

P0 accepts ordinary, unencrypted `.xlsx` packages with bounded dimensions, preformatted cells, no macros/embedded executables/external relationships, and either four-column T-account blocks or a conventional flat journal. It can preserve opaque inert parts byte-for-byte but does not promise to understand them. Refuse packages whose unsupported features could affect accounting semantics. In particular refuse signed packages, workbook encryption, `.xls`, `.xlsb`, `.xlsm`, Power Query/data connections, pivot-driven posting workflows, embedded OLE/ActiveX, DDE/external formulas and unsupported dynamic formula behavior.

Excel Table expansion, row insertion and formula propagation are outside P0. A real table is supported only inside preallocated blank rows already covered by its table range. A plain journal range with stable headers and preformatted blank rows is simpler. Do not silently convert an Excel Table to a plain range.

## Onboarding pipeline

1. Store immutable original and SHA-256; never round-trip it through an authoring library just to inspect it.
2. In an isolated inspector, validate ZIP and XML before extracting bounded package metadata. Include content types, relationships, worksheets/IDs, cells/types/styles, formulas and caches, merges, hidden rows/columns/sheets, table ranges, names, sheet/workbook protection, standard **and extension** validations, instructions and chart-of-account anchors.
3. Build a deterministic evidence index with source sheet/cell references and stable evidence IDs. Only relevant instructions, header neighborhoods, styles and a bounded sample of existing posting rows go to VSI; no entire workbook dump and no student identity fields.
4. VSI proposes a mapping using those evidence IDs. It cannot authorize writes. Deterministic software checks ranges, headers, overlaps, existing formulas and protection, and derives candidate writable cells.
5. Owner confirms mapping and accounting context once: currency/unit, period, company payment accounts, input tax policy, account roles and baseline report. No mapping is active before confirmation.
6. Persist immutable mapping revision and canonical layout compatibility hash. Display confidence as evidence coverage/missing decisions, not an invented probability of correctness.
7. At run start recompute structural compatibility and current occupancy. Routine app-approved appends do not need an LLM onboarding call. A changed sheet name, account header, formula, merge, validation or instruction triggers confirmation of a new mapping revision.

Keep static mapping separate from per-run reservations. Static authorized regions are necessary but insufficient: the effective write set is the intersection of confirmed mapping, compatible source, safe blank slots and admitted plan. No model may enlarge that intersection.

## T-account adapter

Find account headers by matching actual chart IDs and header text, then combine merged-header bounds, repeated four-column styles, border geometry, reference validation and existing debit/credit examples. Headers can span two rows and blocks can appear anywhere horizontally or vertically. Account IDs are strings; similar labels such as 2730 and 7510 cannot be merged.

A slot consists of a reference/amount pair on one side. It is blank only if both cells have no formula, value, shared/inline text, comment requiring preservation, or merged-child role. A numerical zero is occupied, not blank. A single half-filled pair requires mapping review. Never use `max_row + 1` for a T-account.

Reserve slots deterministically by account, side, ascending row, within confirmed bounds. When a compound entry has one contra-reference per row, expand it into pairwise edges. For a two-debit/one-credit purchase, create two credit rows in the payment account, each referencing the associated debit account. The semantic accounting line remains one credit total; slot allocation records the split and conservation checks ensure it is exactly the same total. Multiple-debit/multiple-credit entries require an explicit allocation matrix; defer P0 cases without an unambiguous pairing.

Do not insert transaction descriptions into reference columns. Receipt/date/run linkage lives in the database and downloadable audit JSON. This preserves the user's spreadsheet conventions at the cost of app-dependent provenance for old-style T-accounts.

## Journal adapter

Recognize a confirmed header row with logical fields: date, transaction/reference ID, account ID, description, debit and credit; optional currency. Header synonyms can be suggested by the model, then confirmed. Support either separate debit/credit numeric columns or one amount column with an explicit side column, never an unconfirmed signed-amount convention.

One accounting line occupies one preformatted blank row. Write dates as Excel serial numbers using the workbook's 1900/1904 date system and existing date style; do not write locale date strings. IDs are literal text. Amounts are numeric major units, converted from exact minor units. Account identifiers retain their intended text representation and leading zeros.

Require all writable columns to have known types and all required fields to fit. If unrelated formulas exist in the candidate row, preserve them and exclude their cells from writes; the row can be used only when all affected formula semantics are supported. Preserve header row, table definition and autofilter. Stop with `NO_SAFE_SLOTS` when capacity is exhausted.

## Mapping contract

Version: `ledgerflow.mapping.v1`. See [DATA_SCHEMAS](DATA_SCHEMAS.md) for fields. The mapping stores:

* original fingerprint and current compatible layout hash;
* ordered sheets, sheet IDs and relationship-resolved XML parts;
* accounting instructions with source anchors and hashes;
* chart/account IDs, names, evidence, account roles, header locations and layout;
* exact candidate debit/credit/reference ranges or journal column bindings;
* immutable protected/formula/opening-balance/sensitive regions;
* formula dependency locations, caches and supported recalculation policy;
* money exponent, workbook major-unit convention, date system and period policy;
* preservation manifest, feature compatibility decisions and mapping revision;
* confirming actor/time, policy revision and baseline acknowledgement if any.

A mapping may cover a known limited subset of accounts only if the UI says so and transactions involving other accounts are rejected. For the inspected workbook, all 32 are documented in [SSE_WORKBOOK_AUDIT](SSE_WORKBOOK_AUDIT.md).

## Safe writer strategy

The generated Python must create the actual candidate workbook. Provide a small, versioned workbook helper in the execution image that can read the admitted plan and patch designated cells; the model still generates the program that selects operations, checks plan invariants, calls the helper and produces output. The supervisor does not silently substitute a hardcoded filler if code generation fails.

For the P0 preservation writer:

1. Parse package with secure, bounded readers. Resolve sheet part by workbook relationships, not sheet order assumptions.
2. Require target cells to already exist in supported XML form. Match each cell exactly once in its actual worksheet namespace, compare source value/style to the reserved precondition, and reject ambiguous matches.
3. Change only the targeted cell's payload/type while preserving its coordinate, style and all unrelated attributes. Emit money as finite base-10 numeric major units. Emit references/IDs as explicit `inlineStr` cells using escaped XML text. Do not add shared-string entries or formula elements.
4. Use a token-aware span editor to replace complete supported cell elements, preserving **all bytes outside those spans**. This is deliberately narrower than arbitrary regex XML rewriting or whole-tree serialization. Reject unsupported encodings, duplicate coordinates or lexical ambiguity; do not guess.
5. For calculation metadata, optionally change only `calcPr` in `xl/workbook.xml` to request automatic full recalculation on load. Preserve all other bytes, protection and namespace declarations. This is an explicit allowlisted metadata diff, visible in validation. No broad workbook rebuild.
6. Rebuild the ZIP without duplicate names and with bounded stored/deflated members. Preserve unchanged member uncompressed payload bytes, names, order and relevant ZIP metadata. Whole-file ZIP binary equality is not promised because recompression can differ.
7. Do not alter formulas, calc chain or cached values except under an explicit, separately verified cache policy. P0 never adds formulas. Requesting recalculation is not proof of recalculation.

This writer is a substantial P0 task. Limit it to observed cell forms and safe refusal; do not spend the event building a general OOXML editor. If it cannot be implemented reliably, use a documented openpyxl-compatible **simple** workbook profile for the first live path and keep the actual SSE workbook in read-only analysis. Do not claim SSE write compatibility until extension/protection/native-opening tests pass.

The [openpyxl tutorial](https://openpyxl.readthedocs.io/en/stable/tutorial.html) warns that unsupported objects may be lost when loading and saving. Use openpyxl for read-only convenience or an independently classified simple profile, not a preservation guarantee. [XlsxWriter](https://xlsxwriter.readthedocs.io/faq.html) cannot edit existing files and is suitable only for event-created fixtures. Python `zipfile` and a secure XML parser suit the package-preserving path; their use still requires explicit archive limits.

## Formula and balance policy

Use exact integer minor units for all new financial checks. Values written to Excel use exact decimal strings with exponent 2; do not rely on binary floating-point equality. Bound money to a safe, documented maximum of 10^12 minor units per line for P0, so conversion and presentation remain controlled.

An initial baseline report classifies every existing formula in account amount cells. For the SSE workbook, literal-reference sums and a numeric constant can be independently evaluated. Other formula-valued historical postings require a supported evaluator or a hold. Cached values are never treated as freshly computed proof.

There are three distinct checks:

1. **New journal balance:** sum admitted debits equals sum admitted credits, exactly.
2. **Observed workbook delta:** each actual amount/reference change equals its reserved expected value; per-account/side deltas equal the plan, including split contra rows.
3. **Baseline integrity:** existing values and formula text unchanged; independently evaluated formula-valued postings do not change through new precedents; baseline imbalance is reported separately.

A full-workbook “balanced” label is allowed only when complete opening and historical balance analysis supports it. If a reviewed baseline is already unbalanced, a valid new delta can be labeled “new posting balanced; existing discrepancy remains.” Default onboarding blocks unacknowledged baseline mismatches.

LibreOffice headless is **P1 isolated preview/recalculation only**, with macros disabled, no links/network and a disposable profile. It can rewrite package features, so never replace the approved preservation candidate with its conversion output. Compare Excel/LibreOffice behavior on a disposable copy, mark preview caches as separate, and request native Excel recalculation when appropriate. [LibreOffice parameter reference](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html)

## Independent verification algorithm

The verifier image has trusted code, no generated modules, no write access to source/candidate, no network and a fresh filesystem. Use a different data path from the writer: reparse both complete packages and derive an inventory/diff instead of replaying the writer's manifest.

* Validate both packages independently, including duplicate member/cell names and resource ceilings.
* Compare member set and byte hashes. Only reserved worksheet parts and optional exact `calcPr` metadata change may differ.
* Confirm all bytes outside reserved worksheet cell spans are equal, including x14 validations and namespace declarations. Verify parsed structures as an additional check.
* Inventory formulas, styles, merges, protection, names, links and all non-target cells before/after. Any unauthorized change fails.
* Derive the full actual cell diff, including value types and formulas, and require exact set equality to the admitted operation list. Extra benign-looking changes fail too.
* Check source preconditions: target truly blank, compatible mapping, current period policy, no formula dependency conflicts, no reserved opening/sensitive region.
* Parse each amount without float rounding; compare against expected integer minor units. Validate references against chart IDs and edge allocation.
* Recompute new and baseline accounting checks and report limitations explicitly.
* Require candidate SHA-256 and size from host-collected immutable bytes. Report hash binds base, plan, mapping, policy and candidate.

The host validates the bounded verifier-report schema, checks invocation identity and recomputes hashes. A report from the generated workload cannot stand in for this verifier. Negative tests deliberately corrupt the candidate, remove x14 validations, alter a style, and preserve a balanced sum while changing the wrong account.
