# LedgerFlow — Apple platform handoff

## Latest delivery — local agent application

The Mac application now starts its own persistent HTTPS runtime (`native/desktop/server.py`) and opens an owner session automatically. It no longer depends on a manually started Vite/API pair for normal use. The primary screen is the actual language-agent conversation with an adjacent working dossier. The original outlined wordmark is retained; the app icon is now a folded LF monogram. Build the local application with `python3 native/macos/build.py` (no URL argument). Detailed current setup and usage are in `native/desktop/README.md`; this local path supersedes the earlier public-origin-only instructions below.

iPhone association is implemented for the local runtime: scan a single-use, two-minute QR in the native iOS app, with exact certificate fingerprint trust and a choice of full-workspace or capture-only permissions. The Mac must stay awake with LedgerFlow running. Closing the Mac window leaves the service active; quitting the application stops it. No public relay or Vultr production deployment is claimed.

The real configured vision model, generated code in Docker, independent validation, protected approval, downloaded workbook hash, phone-session sharing and restart persistence passed a fresh synthetic JPEG end-to-end check. See `artifacts/agent-runtime/live-verification.json` and `browser-verification.json`. A signed device-target iOS build subsequently succeeded in Xcode 27.2 beta (located in Downloads, while the global CLI selection still pointed to Command Line Tools). Physical QR/camera behavior and standalone distribution remain unverified. The local runtime reuses the accounting reference routes and is a single-company implementation; it is not the unfinished multi-tenant production scaffold.

Design revision, 27 November 2026: the shared client now uses the workbench described in `DESIGN.md`. Overview combines a compact document queue with actual backend execution events; transaction review keeps the receipt beside the proposed entry and verified cell changes. iPhone home prioritizes capture and expense status. The supplied logo is retained. TypeScript, production build, 15 frontend unit tests and 11 browser integration checks passed after the revision. Visual confirmation covered 1512px, 1280px and 393px, light and dark appearance, without horizontal page overflow. No production backend or accounting rule changed during this design pass.

27 November 2026. This delivery implements the shared client and a thin native macOS window. **No public Vultr service exists yet**, as confirmed by the infrastructure owner. Live Vultr inference, public HTTPS capture and physical iPhone testing remain release gates. Local verification used synthetic documents, explicitly mocked inference, real isolated Docker execution and the existing independent verifier.

## Architecture and scope

The existing React 19 / Vite / TypeScript application already implemented cookie authentication, document upload, workbook detection, accounting review, hash-bound approval, version downloads and SSE. It remains the single product client. The accounting package and production API implementations were not rebuilt.

- **Mac:** shared React financial workspace, also available in a real AppKit/WKWebView application window. Native menus, window resizing, back/forward gestures, file picker and save dialog wrap the same server application. No JavaScript-to-native execution bridge exists.
- **iPhone:** responsive application, installable PWA and native Xcode project at `native/ios/LedgerFlow.xcodeproj`. The SwiftUI/WKWebView shell reuses the mobile interface, with QR association and native workbook sharing. An owner association can manage the full workspace; capture-only sessions retain employee permissions. See `native/ios/README.md`. Signed device-target compilation and simulator tests now pass; physical QR/camera behavior remains unverified.
- **Web:** complete financial application remains browser-accessible; it is not replaced by a landing page or camera-only interface.

The native shells reuse the existing screens and contracts. The iOS SwiftUI entry, WKWebView container, asset catalog, Debug/Release configuration, hosted Swift Testing target and shared Xcode scheme are included. Xcode 27.2 beta was found in Downloads; the global CLI selection still points to Command Line Tools, so terminal builds use a per-command DEVELOPER_DIR override. The signed device-target build and 11 simulator test cases pass. Physical QR/camera behavior remains unverified. The current macOS binary is arm64, targets macOS 13+, and has a local ad-hoc signature, not notarization or an App Store signature.

## What changed

- Eight financial navigation destinations: Overview, Transactions, Receipts, Excel Workbooks, Agent Activity, Security, Audit History and Settings.
- Real API-derived counts and recent documents, with no invented customer data or performance claims. Counts describe the API's returned list, not an unbounded historical total.
- Searchable document list with filters, a keyboard/pointer-resizable list/detail split, contextual actions, original document preview, extracted facts, debit/credit proposal, VAT, existing cell diffs and approval controls.
- Existing workbook inspection and T-account review remain intact; drag-and-drop import and explicit per-workbook navigation/version links were added.
- Agent Activity uses the existing backend SSE events and snapshots. Sandbox duration and token counts are displayed only when reported; missing telemetry reads “Not reported”. Generated code and errors are escaped text.
- Employee home, expenses, detail requests and profile share the same authenticated backend. Corrections include current run/transaction revisions and only supported receipt fields. Finance-only questions stay with finance.
- Upload retries retain the document identity and idempotency key. The UI waits for document normalization before creating a run, refreshes its permitted workbook base and cancels XHR on navigation. Preview object URLs are revoked.
- Light/dark/system appearance, safe areas, 44px mobile controls, reduced motion, gated hover, input sizes that avoid iPhone zoom, keyboard shortcuts and native browser dialogs for continuity.
- Forest/ivory tokens and the supplied outlined LedgerFlow wordmark are reused. The wordmark is not retyped in an approximate font. Brand variables live in `frontend/src/styles.css`; platform structure in `frontend/src/platform.css`.
- Production builds hide development invite shortcuts. API unavailability is distinguished from being signed out. Sign-out failures retain the CSRF token for a retry. Session expiry clears the client view.
- Install manifest, icons and a public offline explanation. The service worker never caches API responses, receipts, workbooks, authentication or the main HTML response; financial mutations are never queued offline.
- A regression in the existing development sandbox supervisor discarded logs on timeout. The narrow fix retains bounded diagnostic stdout/stderr, still destroys the container and discards candidate artifacts. A regression test covers this. No accounting validation rule was changed.
- The existing Vitest development dependency was updated from 3.2.7 to 5.1.2 after npm audit identified vulnerable transitive dependencies. Audit then reported zero vulnerabilities for both production-only and all dependencies.

## Launch locally

From `/Users/petrinolann/Coding/vultr`:

```sh
UV_CACHE_DIR=/tmp/ledgerflow-uv-cache uv sync --extra dev
npm --prefix frontend ci
npm --prefix frontend run build
```

Start the existing **development** service, with mocked inference explicitly selected and the existing Docker image available:

```sh
PORT=8788 VULTR_INFERENCE_API_KEY= .venv/bin/python frontend/dev-mock-api/server.py
```

In another terminal:

```sh
cd /Users/petrinolann/Coding/vultr/frontend
LEDGERFLOW_API=http://127.0.0.1:8788 npm run dev -- --port 5174
```

Open `http://127.0.0.1:5174`. The built application can also be served directly by the existing development service at `http://127.0.0.1:8788`. Demo invite codes belong only to this development service: `owner-demo`, `accountant-demo`, `employee-demo`. Its in-memory data is lost on restart. Docker Desktop and the `python:3.12-slim` image are required for accounting execution; no host-execution fallback was added.

The local Mac client was built and launched with:

```sh
python3 native/macos/build.py
open native/macos/build/LedgerFlow.app
```

For a deployed origin, rebuild with the actual HTTPS origin, without paths, query strings, tokens or credentials:

```sh
python3 native/macos/build.py --url https://YOUR-LEDGERFLOW-HOST
open native/macos/build/LedgerFlow.app
```

The native application contains no backend or secret. Its cookie store is separate from Safari, so sign in in the app. Download destinations are selected with the macOS save dialog, preferring the local singular `~/Document`, then `~/Coding`; the original workbook is never overwritten automatically.

## iPhone and public browser access

After deploying the full backend and built client to the **same public HTTPS origin on Vultr**:

1. Open the app in iPhone Safari and sign in with a provisioned employee invite.
2. Optionally choose Share → Add to Home Screen. Safari on Mac also supports Share → Add to Dock.
3. Scan a receipt, check the preview and confirm. Capture uses the system camera/file picker. It does not implement automatic edge detection, perspective correction or a native VisionKit scanner.
4. Keep the financial workspace open on Mac. Polling refreshes the permitted run list every four seconds; the selected run uses backend SSE plus snapshot polling.
5. Finance reviews the exact independent diff, approves the hash tuple and downloads the new workbook version. The employee sees “Booked” after the same backend run commits.

`Scan with iPhone` generates the QR **locally**, with no external QR service. The standard QR is an application link plus an optional workbook hint; it grants no authority and requires the employee's own session. Loopback links are deliberately not shown as usable phone QR codes. No public HTTPS deployment or real phone capture was available to test here.

The optional temporary-pairing client follows `docs/API_CONTRACT.md` §Optional P1 mobile pairing. It requests `POST /pairings` with `{workbook_id}`, expects `{pairing_id, fragment_token, expires_at}`, puts the bearer only in the URL fragment, and exchanges it in the body of `POST /pairings/exchange` with `{token}`. Closing the dialog requests `DELETE /pairings/{id}`. The exact request-body field names are an integration proposal because the contract does not specify them. **These endpoints do not exist in the current production scaffold or development server.** A 404 is explained; the application does not manufacture employee permissions. Before enabling this route, the backend must enforce atomic single use, a two-minute expiry, upload-only workbook scope, role/tenant checks, CSRF/origin checks and revocation. Client countdowns are not authorization.

## Build and packaging

```sh
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run package:web
python3 native/macos/build.py --url https://YOUR-LEDGERFLOW-HOST
```

`artifacts/apple-platform/LedgerFlow-web-client.zip` contains only `frontend/dist`. It includes no server data, `.env` or credentials. Serve it at the same origin as `/api/v1`, preserve backend `Cache-Control: no-store`, disable proxy buffering for SSE and use valid public TLS. Never deploy `frontend/dev-mock-api/server.py` as the production hackathon agent. Follow the existing Vultr deployment runbook for actual inference and isolated execution.

PWA icons are included in the client assets. To regenerate them with Pillow installed:

```sh
.venv/bin/python frontend/scripts/build-icons.py
```

## Verified results

| Check | Observed result |
| --- | --- |
| TypeScript and Vite production build | Passed |
| Frontend unit tests | 15 passed: existing money/approval/SSE tests plus status presentation, fragment-only pairing, preview origin, reported telemetry, CSRF, upload identity, non-JSON errors and logout failure |
| Existing `tests` and `accounting/tests` | 58 passed; pre-existing framework deprecation / openpyxl feature warnings |
| Development sandbox, API and VSI adapter suite | 16 passed after repairing timeout log retention; real Docker used where required, VSI adapter exercised against its existing local fake |
| Browser integration smoke | 11 passed on Chrome: real HTTP authentication, workbook import, mapping, employee upload, identical desktop run ID, split resize, event monitor, appearance persistence, mobile portrait/landscape overflow and uncaught-error checks |
| Approval continuation | 4 passed on the exact captured synthetic run: independent verification, hash-bound commit and download, employee “Booked”, retained original/committed versions |
| PWA smoke | 3 passed: public-only cache allowlist, available manifest/icons, offline explanation without financial data |
| macOS wrapper | Swift 6 compilation targeting macOS 13+ passed; signature verified; application launched; native WebKit login and financial overview observed |
| npm audit | 0 vulnerabilities, production-only and all dependencies |

The successful receipt was `run_4294c8877cbe4f1d`, producing version `ver_96a4adb76b7046ef`. Reports and the downloaded **synthetic** verified workbook are under `artifacts/apple-platform`. Its bytes were SHA-256 checked against the backend's committed artifact hash. Screenshots are local under `~/Coding/vultr/artifacts/apple-platform`, outside iCloud Documents.

Docker Desktop intermittently returned HTTP 500 during this session. One later clean browser run correctly stopped at `FAILED / SANDBOX_UNAVAILABLE`; it was not counted as a successful accounting commit. The original phone-captured run had already passed real Docker execution and verification and was then committed with a separate guarded continuation test. The sandbox suite subsequently passed 16/16. This evidence is local and does not establish production Vultr readiness.

To reproduce browser tests, start a **fresh** development service and frontend so there are no already-committed synthetic duplicates:

```sh
LEDGERFLOW_TEST_URL=http://127.0.0.1:5174 npm --prefix frontend run test:browser
LEDGERFLOW_TEST_URL=http://127.0.0.1:5174 LEDGERFLOW_REQUIRE_COMMIT=1 npm --prefix frontend run test:browser
```

Run these on separate fresh service instances; the second deliberately fails if Docker execution or verification is unavailable. To test the built PWA, point `LEDGERFLOW_TEST_URL` at the development service serving `frontend/dist` and run `npm --prefix frontend run test:pwa`. Browser tests use installed Google Chrome. The guarded `e2e/approve-existing.mjs` accepts an explicit loopback synthetic run ID and refuses non-development backends and documents whose hash differs from synthetic E1.

## Remaining release gates and platform limits

- Implement/deploy the existing authenticated API contract and worker on Vultr. At inspection, both production API directories exposed only health routes. The client will report errors against that scaffold; it will not fall back to mocked inference.
- Configure real Vultr Serverless Inference and isolated Vultr sandbox execution, then rerun the existing backend contract checker and full end-to-end test against the public origin. This delivery did not use or expose credentials and provisioned no cloud resource.
- Temporary upload-only pairing requires the missing backend endpoints. Independent authenticated employee capture is the current functional path.
- A physical iPhone, real camera image formats, keyboard, safe areas, Safari/PWA installation and native feel still need hardware validation. Browser mobile emulation is not hardware testing.
- JPEG/PNG up to the existing 10 MB API limit are supported. PDF and HEIC are explicitly refused; no unsupported server capability is implied. Browser/PWA haptics are not promised on iPhone.
- The current native iOS device-target build is signed and validated using the user's selected team. Launching the updated binary awaits unlocking the connected iPhone; QR association and camera behavior on physical hardware remain to be checked. No App Store submission, notarization, notification setup or paid Apple membership action was performed.
- The local macOS wrapper is not a distributable notarized release. Authentication, downloads and production reliability must be retested at the real HTTPS origin; local launch/login were verified.
- Audit History shows the API's recorded committed/rejected/cancelled runs and their existing detail/version links. It does not claim a new tamper-proof audit backend or invent missing rejection metadata.
- The original SSE assignment was never opened, modified, renamed or moved by this work. The UI and end-to-end demonstrations used repository synthetic fixtures. The existing accounting regression suite also read its already-present anonymized SSE fixture, without changing the original assignment.

References: [Apple sidebar guidance](https://developer.apple.com/design/human-interface-guidelines/sidebars), [Safari Add to Dock](https://support.apple.com/en-gb/guide/safari/ibrw9e991864/27.0/mac/27), [MDN service worker caching](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Caching), [local QR generation API](https://github.com/soldair/node-qrcode).
