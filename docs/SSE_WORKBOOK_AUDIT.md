# SSE workbook: direct inspection

## Source and method

Inspected `/Users/petrinolann/Downloads/Copy of Assignment_1_Common_transactions_2026.xlsx` after the user directed the search to Downloads. Its accounting assignment structure matches the requested SSE T-account workbook; there is no explicit SSE identifier proving institutional provenance in the fields examined. A second accounting file was considered by sheet metadata and was not used as the target.

Source size: **28,937 bytes**. SHA-256: `3be1ead9bff5f0ce078ba64a6aa58f71acf5d587b798f6ac9c6cdacafdf051f0`.

Method: read-only ZIP member inventory, workbook relationships, all worksheet cells, shared strings, styles, merges, normal and extension validation records, formula text/cached values, names, protection and relationship targets. No save, export, macro execution, Excel native opening or recalculation occurred. Raw findings and per-part hashes are local in ignored `research/private/sse-workbook-inspection.json`. No original bytes were modified.

This audit records package evidence. It does not prove that Excel will accept a future edited package or preserve every proprietary behavior.

## Worksheets and contents

| Sheet | XML member | Used dimension | Serialized cells | Nonempty cells | Formula cells |
|---|---|---|---:|---:|---:|
| Instructions | `xl/worksheets/sheet1.xml` | A1:H24 | 125 | 8 | 0 |
| T-Accounts | `xl/worksheets/sheet2.xml` | A1:AA79 | 934 | 197 | 6 |
| Chart of accounts | `xl/worksheets/sheet3.xml` | A1:B33 | 65 | 65 | 0 |

The T-Accounts sheet has student identity inputs in merged C2:M2 and C3:M3. Values are intentionally omitted from this public-safe report. The upper-right area beginning U1 contains an explanatory example, not an additional account. Account headers occupy four columns and are arranged both across and down the sheet.

Instructions A3:H11 explain the four-column layout: debit contra-reference, debit amount, credit contra-reference, credit amount. Reference columns are light grey and amount cells white. Contra accounts must use square brackets and no unrelated descriptions in those columns. Instructions A21:H24 request preserving the sheet structure. Although the prose says the sheet is not locked, the package separately has a **workbook structure lock**, discussed below.

The chart has 32 bracketed account IDs in A2:A33 and their names in B2:B33. Never substitute a generic Swedish account catalog for these actual account IDs.

## Complete account map

Columns below are `debit reference / debit amount / credit reference / credit amount`. Row bounds exclude account headers. They are candidate regions, not permission to overwrite occupied cells. Dates, receipt IDs and descriptions have no designated slots in this layout; store them in the app audit registry.

| ID | Account | Header anchor | Posting rows | Columns |
|---|---|---|---|---|
| 1110 | Buildings | A7 | 8:10 | A / B / C / D |
| 1220 | Equipment and tools | A12 | 13:15 | A / B / C / D |
| 1510 | Accounts receivable | F7 | 8:20 | F / G / H / I |
| 1690 | Subscribed capital unpaid | A17 | 18:20 | A / B / C / D |
| 1910 | Cash | K7 | 8:20 | K / L / M / N |
| 1940 | Bank account | P7 | 8:20 | P / Q / R / S |
| 2081 | Share capital | A23 | 24:27 | A / B / C / D |
| 2082 | Unregistered share capital | F23 | 24:27 | F / G / H / I |
| 2091 | Profit/loss brought forward | K23 | 24:27 | K / L / M / N |
| 2350 | Bank loans | P23 | 24:27 | P / Q / R / S |
| 2440 | Accounts payable | A29 | 30:45 | A / B / C / D |
| 2610 | Output VAT 25% | F29 | 30:45 | F / G / H / I |
| 2640 | Input VAT | K29 | 30:45 | K / L / M / N |
| 2650 | VAT payable | P29 | 30:34 | P / Q / R / S |
| 2710 | Staff tax | A47 | 48:51 | A / B / C / D |
| 2730 | Employer social charges | F47 | 48:51 | F / G / H / I |
| 2898 | Unclaimed dividends | K47 | 48:51 | K / L / M / N |
| 3001 | Sales 25% VAT | A55 | 56:59 | A / B / C / D |
| 3973 | Capital gains on machinery/equipment | F54 | 56:59 | F / G / H / I |
| 4010 | Purchases of goods | K55 | 56:59 | K / L / M / N |
| 5010 | Rent for premises | P55 | 56:59 | P / Q / R / S |
| 5170 | Repairs and maintenance on own property | A61 | 63:66 | A / B / C / D |
| 5420 | Software | F62 | 63:66 | F / G / H / I |
| 6110 | Office supplies | K62 | 63:66 | K / L / M / N |
| 6210 | Telecommunications | P62 | 63:66 | P / Q / R / S |
| 6540 | IT services | A68 | 69:72 | A / B / C / D |
| 6570 | Banking costs | F68 | 69:72 | F / G / H / I |
| 6810 | Travel tickets | K68 | 69:72 | K / L / M / N |
| 7210 | Salaries to employees | P68 | 69:72 | P / Q / R / S |
| 7510 | Employer social charges | A75 | 76:79 | A / B / C / D |
| 8310 | Interest income from current assets | F74 | 76:79 | F / G / H / I |
| 8410 | Interest expenses | K75 | 76:79 | K / L / M / N |

Merged headers F54:I55, A61:D62 and F74:I75 mean “header row plus one” is an incorrect general algorithm. Use the merged header's bottom row and actual paired cells/borders to derive the first posting row.

## Opening balances

| Account | Reference cell | Amount cell | Side | SEK |
|---|---|---|---|---:|
| 1110 | A8 | B8 | debit | 360,000 |
| 1220 | A13 | B13 | debit | 530,000 |
| 1510 | F8 | G8 | debit | 85,000 |
| 1910 | K8 | L8 | debit | 50,000 |
| 1940 | P8 | Q8 | debit | 195,000 |
| 2081 | C24 | D24 | credit | 400,000 |
| 2091 | M24 | N24 | credit | 230,000 |
| 2350 | R24 | S24 | credit | 570,000 |
| 2440 | C30 | D30 | credit | 20,000 |

Opening debits and credits both total SEK 1,220,000. All `[OB]` reference cells and paired amounts are permanently excluded from write slots.

## Existing postings and baseline defect

There are 40 occupied debit amount cells and 37 occupied credit amount cells across the mapped accounts, including nine opening balances and three formula-valued postings. Examples include bank/receivable settlement I8/Q10, a cash-to-bank transfer N8/Q9, purchases N9/N10 and L56/L30, and software G63 with VAT L33. Existing entries are not empty template examples and must not be erased.

Summing **all** account amount cells yields:

| Measure | SEK |
|---|---:|
| Full mapped debit amounts | 1,908,465 |
| Full mapped credit amounts | 1,820,489 |
| Debit excess | **87,976** |
| Visible W22 cached check total | 1,632,399 |
| Visible X22 cached check total | 1,632,399 |
| Visible W24 cached difference | 0 |

The three posting formulas were independently reconciled from literal precedents: G30 = 2,500 + 15,500 + 10,250 = 28,250; N30 = 1,050 + 1,200 + 174 + 4,375 + 6,500 + 2,900 + 1,475 + 1,075 = 18,749; S30 is the constant formula 28,250. Thus the full-account sum above does not rely on unverified cached posting results.

Two observed debit postings, G48 and B76, each contain 43,988. Their sum equals the 87,976 excess. That identifies an investigation lead, **not authorization to change either side or assert the intended accounting treatment**. This preparation made no correction.

Default production behavior: hold onboarding for review of the baseline mismatch. For an explicitly supervised demonstration, a reviewer may acknowledge this exact baseline defect and permit only independently balanced deltas, while the UI continues to display the existing 87,976 difference. Record the acknowledgement with the base hash and report hash. Never label that workbook globally “balanced” or suppress the warning. A fresh synthetic balanced workbook is the cleaner primary live-demo choice.

## Formula inventory and risk

All six formulas are on T-Accounts. Formula text is preserved exactly.

| Cell | Formula role | Cached result |
|---|---|---:|
| W22 | Selected debit sums, not all debit regions | 1,632,399 |
| X22 | Selected credit sums, not all credit regions | 1,632,399 |
| W24 | `W22-X22` | 0 |
| G30 | `SUM(I30:I32)` | 28,250 |
| N30 | `SUM(L30:L37)` | 18,749 |
| S30 | Constant formula `28250` | 28,250 |

W22 includes L63 but not a future L64; includes Q8:Q10 but not the occupied Q11. X22 includes S8:S9 but not the occupied S10:S11 or future S12. Existing check formulas cannot verify arbitrary appended entries.

G30 and N30 are **accounting postings expressed as formulas**, not just display totals. Appending a value within their precedent ranges can change a legacy posting after native recalculation. The verifier must detect dependency intersections and block such writes unless an explicit separate workflow approves all induced accounting changes. The P0 demo appends outside these ranges and leaves historical posting formulas semantically unchanged.

## Validation, merges and protection

* Instructions has 3 merged ranges. T-Accounts has 34. Chart of accounts has none. Never write a merged child cell or insert rows/columns.
* No normal `dataValidations` element is present. Instead, Instructions and T-Accounts each contain **one x14 extension list validation**, pointing to `'Chart of accounts'!$A$2:$A$33`. T-Accounts lists many discontiguous reference ranges. A normal-only parser would miss it.
* The candidate demo cells K64, L64, K38, L38, R12 and S12 already exist as blank serialized cells. Their current styles are 12, 7, 12, 16, 12 and 18 respectively. K64, K38 and R12 fall within the corresponding reference validations.
* There is no worksheet `sheetProtection` element in any sheet. Cell styles contain no explicit protection overrides. Excel's default cell-lock behavior becomes relevant only if sheet protection is later enabled.
* Workbook protection has `lockStructure=1` with SHA-512 protection metadata. Preserve it. Do not add/delete/rename sheets, remove protection, or attempt password recovery.
* There are 30 `IQ_*` defined names, including hidden names and numeric constants. No evidence shows they are necessary to these accounting entries; preserve them regardless.

## Package features to preserve

The archive has 27 members: worksheets, styles, theme, shared strings, calc chain, two binary printer settings, core/app/custom document properties, three custom XML items with their properties/relationships, and package relationships/content types. There are no detected VBA project members, embeddings, external-link parts, drawing/chart parts, or `TargetMode="External"` relationships. This is a package inventory observation, not proof of universal safety.

Generic XML reserialization can change namespace prefixes referenced by `mc:Ignorable`, and routine openpyxl saves may drop unsupported extensions. Therefore choose targeted OOXML cell patching, copying every other member's decompressed payload unchanged. Allow only a narrowly specified calculation-properties metadata change when required. Verify unchanged member hashes, worksheet byte preservation outside edited cell spans, all validation extension bytes, merges, protection and formula text. See [EXCEL_ENGINE](EXCEL_ENGINE.md).

## Candidate example, not an executed change

A **hypothetical** SEK 125.00 office-supplies receipt, with explicitly configured SEK 25.00 deductible input VAT and confirmed company-bank payment, admits these abstract lines:

* debit 6110: 10,000 minor units;
* debit 2640: 2,500 minor units;
* credit 1940: 12,500 minor units.

Candidate positions: K64=`[1940]`, L64=100.00; K38=`[1940]`, L38=25.00; R12=`[6110]`, S12=100.00; R13=`[2640]`, S13=25.00. The credit is split so each contra-reference names exactly one account, as required by the workbook. Recheck R13/S13 occupancy and all slots immediately before running. No such receipt or output file has been created here.

This produces eight cell changes, debit/credit deltas both SEK 125.00, and leaves the pre-existing SEK 87,976 imbalance unchanged. New inputs L38/L64/S12/S13 are outside the legacy formula-posting precedent ranges. The visible W24 may remain zero, illustrating why the independent validator matters.

## Concrete mapping handoff

[The proposed JSON mapping](sse-mapping.proposed.json) contains all 32 actual account regions, sheet/part bindings, instructions, opening balances and formula exclusions. It is a **read-only preparation proposal**, not a confirmed runtime mapping. Account roles and policy remain unconfirmed; currency/unit assumptions require owner confirmation. The event engine must re-inspect the actual source before activating it.

[The observed layout fingerprint input](sse-layout-fingerprint.observed.json), [feature manifest](sse-feature-manifest.observed.json) and [independently computed baseline](sse-baseline.observed.json) make its hashes reproducible. Their canonical serialization follows DATA_SCHEMAS. The fingerprint version is explicitly `preparation_observed_layout_v1`; an event implementation with a different fingerprint algorithm must create a new mapping revision rather than pretending this hash came from its own runtime. Student identity values and workbook protection password-hash/salt values are excluded from these publishable JSON files.
