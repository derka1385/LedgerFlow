# Research provenance and unresolved questions

Research date: **26 November 2026**. Sources below are primary publisher/project documentation, public APIs and package registries. “Reviewed” means retrieved/read; it does not mean the advertised capability was exercised.

## Event evidence

| Source | Observation | Limit |
|---|---|---|
| [Vultr event](https://community.vultr.com/e/vultr-agent-runtime-hackathon) | Mandatory infrastructure, execution/containment and submission requirements align with user brief | No explicit pre-event coding authorization found; detailed judging rubric not established |
| [Stockholm registration](https://luma.com/stockholm-nn3n) | Local agenda: 09:00 doors, 10:00 hacking, 19:00 submission; team 2–4 | Confirm onsite agenda and eligibility; event duration is not build duration |
| [Organizer welcome](https://community.vultr.com/d/welcome-to-the-vultr-agent-runtime-hackathon) | Links to credits/submission resources and onsite support | No account credits redeemed or registration performed |

Do not import prizes, team sizes or judging rules from other similarly named Vultr events. The brief's requirements remain the project acceptance checklist even when source pages use shorter descriptions.

## Vultr API and model evidence

| Source | Observation | Limit |
|---|---|---|
| [VSI provisioning](https://docs.vultr.com/products/compute/serverless-inference/provisioning) | Subscription setup; usage-based model prices surfaced in console | No subscription/key provisioned here |
| [Live model catalog](https://api.vultrinference.com/v1/models) | 31 model records; exact IDs, input/output metadata, token prices and datacenter metadata saved | Metadata is not verified inference behavior or entitlement |
| [Tool-calling guide](https://docs.vultr.com/how-to-use-tool-calling-with-vultr-serverless-inference) | OpenAI-style functions/tool calls documented | Example model ID differs from current catalog; no tool call tested |
| [Python inference guide](https://docs.vultr.com/how-to-use-vultr-serverless-inference-in-python) | OpenAI-compatible request integration described | No authenticated request tested |
| [Usage/cost article](https://docs.vultr.com/support/products/compute/serverless-inference/how-do-i-monitor-the-usage-and-cost-of-my-vultr-serverless-inference-subscription) | Generic rates conflict with model-specific live metadata | Console/account billing confirmation still required |
| [Plans API](https://api.vultr.com/v2/plans?per_page=500) | HTTP 200, 140 plans, no remaining pagination; exact published rates saved | No checkout/capacity/provisioning test |
| [Regions API](https://api.vultr.com/v2/regions?per_page=500) | HTTP 200; `sto` identifies Stockholm | Does not establish selected plan stock or inference residency |

`https://www.vultr.com/api/` and the main public pricing page returned 403 through the web reader. Public JSON catalog GETs succeeded directly. The guessed structured-output guide URL was not retrievable; this is **not evidence that structured outputs are unsupported**. Live metadata advertises response-format capabilities; actual request syntax/reliability remains a probe requirement.

Artifacts:

* `research/vultr-models-2026-11-26.json` and `.provenance.json`;
* `research/vultr-plans-2026-11-26.json` and `.provenance.json`;
* `research/vultr-regions-2026-11-26.json` and `.provenance.json`;
* `research/dependency-catalog-2026-11-26.json`, containing source URLs, response hashes, timestamps and version/engine observations.

Catalog downloads were read-only HTTP GETs. They did not deploy resources or send a billable inference request. Provider request latency, financial extraction accuracy, structured-output adherence and throughput are unmeasured.

## Isolation research

| Primary source | Relevant finding |
|---|---|
| [Docker security](https://docs.docker.com/engine/security/) | Kernel/daemon/configuration are separate attack surfaces; daemon access is privileged |
| [Docker run reference](https://docs.docker.com/reference/cli/docker/container/run/) | User, read-only, capability, resource and security controls available; actual runtime must enforce them |
| [Docker seccomp](https://docs.docker.com/engine/security/seccomp/) | Default confinement is useful; disabling it is not a routine compatibility fix |
| [Docker network none](https://docs.docker.com/engine/network/drivers/none) | No external network interface, loopback only |
| [Docker resource policy](https://docs.docker.com/engine/containers/resource_constraints/) | Defaults are not resource caps; swap semantics require care |
| [gVisor Docker integration](https://gvisor.dev/docs/user_guide/quick_start/docker/) | Runtime must be selected/configured; guest dmesg is spoofable and not secure attestation |
| [gVisor platform guide](https://gvisor.dev/docs/architecture_guide/platforms/) | systrap fits VM/no-virtualization environments |
| [gVisor security model](https://gvisor.dev/docs/architecture_guide/security/) | Userspace system interface limits exposure; host policy/application security remain necessary |
| [OpenSandbox](https://github.com/opensandbox-group/OpenSandbox) | Unified lifecycle/file/execution APIs, Docker/Kubernetes integration; underlying runtime determines isolation |
| [E2B BYOC/self-host distinction](https://docs.e2b.dev/byoc) | Managed BYOC differs from self-hosted Embed; current managed providers are not Vultr |
| [E2B Embed](https://github.com/e2b-dev/runtime/tree/main/embed) | Single-machine evaluation package, KVM/Firecracker and multiple exposed services; self-hosting is real but not free operationally |
| [Vultr Microsandbox guide](https://docs.vultr.com/how-to-set-up-agent-sandboxing-on-vultr-cloud-compute) | KVM prerequisite, microVM lifecycle; guide's default internet access does not meet our no-egress policy |
| [Microsandbox upstream](https://github.com/superradcompany/microsandbox) | Current project/OCI/microVM approach; startup marketing is not a local benchmark |

No runtime was installed or benchmarked as part of preparation. Integration-time ranges in DECISIONS are engineering estimates.

## Workbook and application sources

* [openpyxl tutorial](https://openpyxl.readthedocs.io/en/stable/tutorial.html): load/save preservation limitations; read-only/data-only semantics.
* [openpyxl security note](https://openpyxl.readthedocs.io/en/stable/): XML attack protection is not automatic by default.
* [XlsxWriter FAQ](https://xlsxwriter.readthedocs.io/faq.html): existing workbook editing is unsupported; cached formula results are not recalculation proof.
* [Microsoft SpreadsheetML formulas](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-formulas): formula element versus cached value distinction.
* [Python ZIP documentation](https://docs.python.org/3/library/zipfile.html): hostile archive/decompression pitfalls justify streaming limits.
* [Python Decimal](https://docs.python.org/3/library/decimal.html): exact decimal arithmetic; minor-unit integers remain the API accounting representation.
* [LibreOffice command parameters](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html): headless operation/profile requirements; conversion remains a separate compatibility risk.
* [SQLite transactions](https://sqlite.org/lang_transaction.html) and [WAL notes](https://sqlite.org/wal.html): write locking, same-host requirements and patched WAL-reset behavior.
* [Pydantic strict validation](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/): strict validation still needs explicit money/accounting invariants.
* [FastAPI workers](https://fastapi.tiangolo.com/deployment/server-workers/): API process deployment; durable jobs are an architectural choice, not in-request background guarantees.
* [Caddy HTTPS](https://caddyserver.com/docs/automatic-https): automatic certificates depend on working public host/challenge setup.
* [OWASP formula injection](https://community.owasp.org/attacks/CSV_Injection): untrusted text must not become an executable spreadsheet formula.

The actual source workbook was found in Downloads and inspected directly; it was not downloaded from a public source. Provenance and findings are in [SSE_WORKBOOK_AUDIT](SSE_WORKBOOK_AUDIT.md). Personal identity values and raw inspection data are excluded from the publishable handoff.

## Questions left for onsite evidence

Pre-event coding eligibility; exact submission/video rules; actual model entitlement/image/schema syntax/accuracy; reasoning/image token billing; current VM stock; actual runsc policy compatibility; native Excel edited-file opening/recalculation; achievable latency/concurrency; secret-free image build and cleanup proof. Each is a named test or organizer question, not an assumed success.
