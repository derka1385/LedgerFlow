# Architecture decisions and alternatives

Status: design choices for event-time implementation, not measured performance claims. Estimated engineering times assume an experienced team and working account access. Alternatives were researched from primary sources on 26 November 2026.

## ADR-01 — Docker plus gVisor on Vultr

Choose Docker lifecycle tooling with explicit gVisor `runsc` for every untrusted parsing/execution job. The team gets familiar container packaging without exposing generated syscalls directly to the normal shared-kernel container interface. Use a narrow supervisor and independent verification; neither Docker nor gVisor alone secures the whole application.

| Option | Security and compliance | Estimated integration effort | Reliability / latency / cost | Scale and decision |
|---|---|---|---|---|
| Hardened Docker | Namespaces/cgroups/seccomp, shared host kernel; allowed by event | 1–2 h including tests | Familiar; low startup overhead; included VM cost | Fast baseline, weaker isolation; fallback only with explicit limitation |
| Docker + gVisor | Userspace kernel interface plus fixed host policy; runs on Vultr | Additional 30–60 min, timebox initial compatibility to 30 min | Python file workloads plausible; syscall/file overhead needs measuring; same VM | **Primary**, no nested KVM dependency with systrap |
| OpenSandbox | Lifecycle/API abstraction; strength depends on selected runtime and configuration | 1–3 h adoption/hardening, estimate | SDKs/file APIs useful, more server/components to configure | Revisit if team already knows it; not needed for one-shot file jobs |
| E2B Embed | Firecracker microVMs on one KVM-capable Linux host; self-hosted on Vultr is conceptually eligible | 2–4+ h, untested | Additional services/ports, image/template setup; unknown local latency | Real self-host option exists; skip integration risk today |
| E2B Cloud/BYOC | Cloud sandboxes off Vultr fail this brief; managed BYOC currently lists AWS/GCP/Azure | Enterprise setup unsuitable for 9 h | Operational convenience elsewhere, wrong runtime location | Reject for this event |
| Microsandbox | libkrun/KVM microVMs; explicit host virtualization prerequisite | 1–3 h if KVM works, unbounded if not | Fast startup is an upstream claim, not measured here; networking must be disabled explicitly | Strong P1 alternative if VM capability verified early |
| Ephemeral Vultr VM/task | Separate guest kernel and credentials can stay in control plane | 2–4+ h provisioning/reconciliation work | Boot/provision latency, quotas, API failure and orphan billing; no verified timings | Production isolation option; not in request-critical path today |

Sources: [Docker security](https://docs.docker.com/engine/security/), [gVisor platform guide](https://gvisor.dev/docs/architecture_guide/platforms/), [OpenSandbox](https://github.com/opensandbox-group/OpenSandbox), [E2B deployment models](https://docs.e2b.dev/byoc), [E2B Embed](https://github.com/e2b-dev/runtime/tree/main/embed), [Vultr Microsandbox guide](https://docs.vultr.com/how-to-set-up-agent-sandboxing-on-vultr-cloud-compute).

OpenSandbox is an orchestration product, not automatically stronger isolation than its configured Docker backend. E2B's current self-host option is Embed, rather than assuming every self-host deployment needs the older full cloud stack. Its upstream evaluation package exposes multiple services and requires careful firewalling. Microsandbox's official Vultr guide demonstrates internet access by default; sibling isolation is not the same as no egress. These details rule out copying a quickstart and claiming the required policy is already satisfied.

## ADR-02 — Modular monolith, one trusted worker

Choose Python/FastAPI/Pydantic, SQLite, local immutable files and a separate worker process. React/TypeScript/Tailwind compile to static assets; Caddy serves them and proxies the API. Use REST plus SSE. No Redis, Celery, Kubernetes, LangGraph or agent microservices are needed for the P0 state machine. Persist work before returning 202 and use database leases, not in-memory queues.

SQLite is sufficient for one host and short commits. Use a patched SQLite build if enabling WAL; verify actual runtime library version and security backports. If the host's version cannot be established as patched, use rollback journal mode for the demo rather than building a database stack. See [SQLite's WAL-reset documentation](https://sqlite.org/wal.html). PostgreSQL is the next step when multiple app hosts or higher concurrent writes justify it.

SSE gives one-way durable updates without introducing WebSocket connection state. Use GET snapshots on reconnect. A multi-device user does not require peer-to-peer synchronization.

## ADR-03 — Targeted OOXML editing, bounded compatibility

Choose secure ZIP/XML inspection and a narrow cell-span writer for the actual SSE file. It contains x14 validations and opaque parts that a routine authoring-library save could alter. Verify preservation independently. No row insertion, formula creation, new sheets or table expansion in P0.

| Excel option | Existing workbook | Preservation | Time/reliability tradeoff |
|---|---|---|---|
| openpyxl | Reads/modifies `.xlsx` | Not all features; extensions/objects require explicit checks | Fast for classified simple profiles, not the default SSE save path |
| XlsxWriter | Cannot read/edit existing file | New files only | Good for event-created fixtures, unsuitable as adaptive editor |
| Direct OOXML | Can patch existing parts narrowly | Unchanged payload bytes can be preserved | More engineering; constrain to observed existing cells and safe refusal |
| pandas | Useful table analysis | Re-export is not workbook-preservation strategy | Avoid as editor for formatted accounting workbooks |
| LibreOffice headless | Can open/recalculate/convert | Conversion may rewrite features | Separate optional preview/check copy; never silently swap into approval |

Sources: [openpyxl tutorial](https://openpyxl.readthedocs.io/en/stable/tutorial.html), [XlsxWriter FAQ](https://xlsxwriter.readthedocs.io/faq.html), [Microsoft formula/cache model](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-formulas), [LibreOffice parameters](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html).

The SSE baseline itself is inconsistent. Reject the tempting choice of trusting its zero check or silently “fixing” it. Default hold, explicitly reviewed baseline acknowledgement for a supervised delta-only demonstration, and a clean synthetic balanced primary demo are safer and more truthful.

## ADR-04 — Two normal model calls, deterministic verification

Choose model-assisted extraction and accounting/code proposals, with software arithmetic and validation. The exact catalog candidates are recorded in [COST_ANALYSIS](COST_ANALYSIS.md). No accuracy ranking was measured. Default choice is provisional until entitlement, image and schema probes pass.

Avoid a tool-calling dependency in the first path. JSON schema output is preferred only after a successful probe; strict local validation remains required. Provider-compatible JSON mode plus bounded repair is the fallback. Switching to another model still uses VSI; no OpenAI, Anthropic or other-provider runtime fallback.

An LLM is useful for heterogeneous labels and reasoning about document/account evidence. It is the wrong tool for exact debit-credit equality, duplicate hashes, XML diffs, money conversion or commit concurrency.

## ADR-05 — Hash-bound approval and immutable versions

Choose approve-and-commit of exact already-verified bytes, atomic current-pointer compare-and-swap and a transaction registry. Reject “approve then regenerate the final workbook,” mutable preview paths, overwriting the source in place or automatically merging stale candidates. These introduce a gap between the human's decision and the financial artifact.

## ADR-06 — No automatic desktop Excel synchronization

The server maintains workbook versions and offers download. The employee phone and accountant desktop share server state via authenticated API/SSE. Do not add a desktop filesystem watcher or overwrite a workbook open in Excel. Existing infrastructure remains usable because the approved artifact is still its workbook format/layout, not because this MVP has a native Excel integration.

## ADR-07 — Invited demo access

Choose a public product URL with invitation-gated financial actions. This meets public browser availability while preventing anonymous compute abuse. Separate employee upload and accountant approval roles. Real identity federation, enterprise retention and financial production compliance are future work, not quietly implied by a hackathon login.

## Reconsideration triggers

Reconsider runtime if Python/OOXML fails under gVisor within the timebox; Excel editing if preservation/native-opening tests fail; model selection if the representative image/schema smoke gate fails; database if multiple app hosts are required; workflow if per-receipt human approval is the throughput bottleneck. Record any changed decision in the final README and demonstration instead of continuing to describe the abandoned architecture.
