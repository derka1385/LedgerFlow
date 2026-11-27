# LedgerFlow frontend

React 19 + TypeScript + Vite 7. No router or UI library: hash routes, plain CSS tokens from `product/UX_SPEC.md`.
Talks only to `/api/v1` (docs/API_CONTRACT.md): cookie session + `X-CSRF-Token`, `Idempotency-Key` on every mutation, SSE for run events.

## Run against the DEV MOCK API (no Vultr credentials needed)

```bash
cd frontend && npm ci && npm run build
```

```bash
LEDGERFLOW_SANDBOX_IMAGE=python:3.12-slim python3 frontend/dev-mock-api/server.py
```

Open http://localhost:8787. The mock serves `dist/` on the same origin. Demo invites: `owner-demo`, `accountant-demo`, `employee-demo`.

- Needs Docker and the sandbox image locally (`docker pull python:3.12-slim` once). Without Docker, runs fail with `SANDBOX_UNAVAILABLE`. `LEDGERFLOW_ALLOW_UNSANDBOXED=1` runs generated code as a local process, labelled UNSANDBOXED everywhere (dev only, never for the demo).
- For hot reload: `npm run dev` (port 5173, proxies `/api` to `LEDGERFLOW_API`, default `http://127.0.0.1:8787`).

## Run against Codex's backend

Serve `dist/` from the same origin as the API, or run `LEDGERFLOW_API=http://<backend> npm run dev`. Nothing in the UI depends on the mock except the "Use a sample" pickers, which only appear when the session says `backend: "DEV-MOCK"`.

## Tests

```bash
npm test
```

```bash
npm run typecheck
```

```bash
python3 -m pytest frontend/dev-mock-api/test_mock_api.py -q
```

The last one, run from the repo root, drives the full HTTP flow including real Docker sandbox runs.

## Screens (hash routes)

| Route | Who | What |
|---|---|---|
| `#/capture` | everyone | Mobile capture: photo or file, preview, submit, live status |
| `#/workbook` | owner (accountant read-only) | Upload, inspection, baseline exceptions, confirm mapping |
| `#/inbox` | accountant, owner | Ready to approve / needs your answer / in progress / done |
| `#/runs/:id` | accountant, owner | Evidence, entry, corrections, cell diff, proof, approval bar, execution monitor |
| `#/versions` | accountant, owner | Version history with downloads (v1 = original upload) |
| `#/security` | accountant, owner | Live containment test (raw runtime output) |

## Real Vultr inference and backend conformance

- Live demo: put the key in the git-ignored repo `.env` (`VULTR_INFERENCE_API_KEY=...`, chmod 600), then `python3 frontend/dev-mock-api/server.py --dotenv`. Model and prompts come from `config/inference.json` (measured choice: `qwen3.8-27b`, `reasoning_effort=minimal`, codegen prompt v2). The start line prints the inference mode, never the key. Without `--dotenv` and without the variable it stays on labelled mocks.
- Measured KPIs for the UI: `GET /api/v1/benchmark/kpis` (`getBenchmarkKpis()`, types `BenchmarkKpis` in `src/lib/types.ts`), built by `python3 benchmark/kpis.py`.
- Check any backend against what this UI needs: `python3 frontend/contract/check_backend.py --help`.
