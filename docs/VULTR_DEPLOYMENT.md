# Vultr deployment runbook

This is an event-time deployment specification. No cloud resources or credentials were created or exercised during preparation. Do not paste documentation examples into a claim of successful deployment.

**Implemented infrastructure option:** [OpenTofu runner module](../infra/opentofu/README.md)
manages the VM, SSH key, firewall and cloud-init bootstrap. It has local schema and
mocked-plan validation; authenticated provisioning and runtime containment remain
unverified. This adds an explicit IaC option to the original manual-first runbook.

## Infrastructure choice

Primary: one Vultr Cloud Compute VM, Ubuntu 24.04, region `sto`, plan candidate `vc2-4c-8gb` (4 vCPU, 8 GiB RAM, 160 GB SSD). The public plan snapshot lists USD 40/month and USD 0.055/hour, with Stockholm among locations. Live capacity, account quotas, tax and the actual checkout charge must be verified in the console. Do not assume nested KVM merely because the VM exists.

Alternative budget plan `vc2-2c-4gb` lists USD 20/month and USD 0.027/hour. Use only one sandbox slot on 4 GiB after measuring all resource overhead. If stronger microVM isolation is chosen later, first prove usable `/dev/kvm` and CPU virtualization; the [Vultr Microsandbox guide](https://docs.vultr.com/how-to-set-up-agent-sandboxing-on-vultr-cloud-compute) explicitly makes this a prerequisite.

Vultr remains central: state, reasoning requests, code dispatch, verification, audit and approved files all run through this backend. Hosting the frontend on Vultr while sending runtime reasoning or sandboxes elsewhere would not satisfy the brief.

## Event-time setup sequence

1. Confirm eligibility to start building; claim authorized event credits using organizer instructions. Verify account billing/limits personally. Do not expose account keys on screen.
2. Provision VM in console, selecting an available supported plan/region and Ubuntu 24.04. Record instance ID, region, selected plan, public IP, OS and charged rate in a private deployment record. A second isolated fallback runner is optional, not assumed.
3. Create a deploy user with SSH key access, disable password/root SSH after testing another session, install security updates and accurate time sync. Keep an open recovery session while changing SSH policy.
4. Vultr firewall: inbound TCP 80/443 publicly for HTTPS, TCP 22 only from team IPs; no public 8000, Docker API, SQLite, runtime socket or development server. Review host firewall and Docker interactions too.
5. Set DNS for an owned hostname to the VM. Use Caddy to serve React build assets and reverse-proxy `/api/*` to a loopback-only FastAPI listener. Configure SPA fallback only for frontend routes, never swallow API 404s.
6. Provision Serverless Inference subscription and obtain its **inference key**, distinct from a Vultr account infrastructure API key. Follow [current provisioning documentation](https://docs.vultr.com/products/compute/serverless-inference/provisioning). Keep infrastructure provisioning manual in P0 so the app needs no account API key.
7. Perform the authenticated model capability gates in [AGENT_RUNTIME](AGENT_RUNTIME.md). Use only exact catalog IDs that pass. Record outcomes honestly.
8. Install Docker from official supported distribution instructions and gVisor from its official installation source; verify downloaded artifacts/signatures/checksums. Record actual versions. Configure runtime explicitly; use `systrap` inside the VM unless tested requirements justify another platform. [gVisor Docker guide](https://gvisor.dev/docs/user_guide/quick_start/docker/)
9. Build pinned execution/inspector/verifier images during the event. Bake dependencies into images. Do not install packages at run time. Inspect image environment/layers for credentials, record digest and run the full policy smoke tests.
10. Create service users, immutable object directories, DB, job staging root and the fixed supervisor protocol. API/worker have no Docker socket permissions. The supervisor alone uses the daemon and host-mounted bounded job workspaces.
11. Run schema migrations, provision owner/accountant/employee invites locally, deploy backend/worker/static bundle, and perform the end-to-end HTTPS phone test.
12. Run containment, approval-race, duplicate and workbook-preservation tests on this host. Publish the demo URL only after it passes the supported path. Record video early; release freeze by 17:00 is the target.

No Kubernetes, managed database, load balancer, per-receipt VM provisioning or autoscaler is required for this first deployment. The manual path needs no Terraform state; the optional OpenTofu path does maintain private state as described in its README.

## Process/service layout

| Process | Identity / access | Restart / bounds |
|---|---|---|
| Caddy | Dedicated web identity; static assets and loopback upstream only | Auto-restart; certificate storage persistent |
| FastAPI | `ledgerapi`; DB/object store via app repository; no Docker | One process initially; bounded requests/uploads |
| Worker | `ledgerworker`; DB, private inference key, job socket | One durable worker; fenced leases; no local generated-code exec |
| Supervisor | Root-owned minimal service; fixed job policy, daemon and staging only | Independent deadlines; idempotent jobs; bounded RPC |
| Reaper | Root-owned fixed reconciliation task | Every 30 seconds; only LedgerFlow job labels/roots |
| Docker/runsc | Host-managed runtime | No TCP API; runtime and cgroup configuration recorded |

Use service-manager sandboxing for API/worker: private temp, no-new-privileges, read-only system paths, explicit writable data paths and restricted environment. The supervisor needs a consciously designed mount namespace: its host-side quota mounts must be visible to Docker for bind mounting. Do not blindly enable a private mount namespace that hides those mounts from the daemon. Test the chosen service settings together rather than assuming individually secure options compose correctly.

The backend must not start durable financial jobs only as ephemeral FastAPI request-background tasks. Persist them before returning 202; a separate worker process owns execution. Keep SQLite on a real local filesystem, not an unreliable network share.

## Environment specification

These are configuration names and defaults, not a secret-bearing `.env` file.

| Variable | Scope | Value / constraint |
|---|---|---|
| `APP_ENV` | API/worker | `demo` initially |
| `PUBLIC_ORIGIN` | API | Actual HTTPS origin; strict origin checks |
| `DATABASE_URL` | API/worker | PostgreSQL URL including credentials; service environment only, never in Git or cloud-init |
| `OBJECT_STORE_ROOT` | API/worker | Private local immutable object root |
| `SUPERVISOR_SOCKET` | Worker | Fixed local Unix socket |
| `VULTR_INFERENCE_BASE_URL` | Worker | Exactly `https://api.vultrinference.com/v1` |
| `VULTR_INFERENCE_API_KEY` | Worker secret only | Never frontend, supervisor or workload |
| `VULTR_MODEL_EXTRACT` | Worker | Candidate `glm-5.3-flash`, only after probe |
| `VULTR_MODEL_PLAN` | Worker | Candidate `glm-5.3-flash`, only after probe |
| `VULTR_MODEL_REPAIR` | Worker | Candidate `glm-5.3`, only after probe; optional |
| `MODEL_REQUEST_TIMEOUT_SECONDS` | Worker | 45 |
| `MAX_MODEL_REQUESTS_PER_RUN` | Worker | 6 |
| `MAX_EXECUTION_ATTEMPTS` | Worker | 2 |
| `MAX_ACTIVE_PROCESSING_SECONDS` | Worker | 300 |
| `SANDBOX_IMAGE_DIGEST` | Supervisor policy | Verified actual execution-image digest |
| `INSPECTOR_IMAGE_DIGEST` | Supervisor policy | Verified actual inspector-image digest |
| `VERIFIER_IMAGE_DIGEST` | Supervisor policy | Verified actual verifier-image digest |
| `SANDBOX_RUNTIME` | Supervisor policy | `runsc`; do not silently fallback |
| `SANDBOX_MEMORY_MIB` | Supervisor policy | 512 |
| `SANDBOX_CPU_LIMIT` | Supervisor policy | 1 |
| `SANDBOX_PIDS_LIMIT` | Supervisor policy | 64 |
| `SANDBOX_TIMEOUT_SECONDS` | Supervisor policy | 30 |
| `SANDBOX_MAX_LIFETIME_SECONDS` | Supervisor policy | 60 |
| `MAX_ACTIVE_SANDBOX_JOBS` | Supervisor policy | 2 on 8 GiB; test |
| `WORKBOOK_MAX_BYTES` | API/inspector | 10,485,760 |
| `IMAGE_MAX_BYTES` | API/normalizer | 10,485,760 |
| `APPROVAL_TTL_SECONDS` | API | 900 |
| `DEMO_DIAGNOSTICS_ENABLED` | API | Owner-only fixed probes; never arbitrary source |

No `VITE_*` or frontend bundle variable may contain credentials. No third-party model-provider fallback is configured. Optional infrastructure API credentials remain in an operator's provisioning context, never in the web runtime.

## HTTPS and mobile

Use a real trusted certificate: phone camera capture and secure sessions require a secure origin. Caddy automates certificate issuance/renewal, but DNS and reachable challenge ports must work. An HTTPS site using a bare self-signed IP certificate is not an acceptable phone-demo substitute. [Caddy HTTPS documentation](https://caddyserver.com/docs/automatic-https)

A public domain resolving to the VM is preferred. If no domain is available, obtain an organizer-approved hostname early. Do not assume a tunnel hosted elsewhere fulfills hosting requirements. Mobile capture uses `accept="image/*"`/camera preference with a file-picker fallback; explicit JPEG/PNG validation still applies. iPhone HEIC uploads receive a clear conversion instruction in P0. Test with the actual demonstration phone before lunch.

SSE proxy must avoid buffering, compression transformations and too-short idle timeouts. Use 15-second heartbeats. Verify a reconnect receives the committed result from durable state.

## Releases, rollback and cleanup

Record source commit, dependency lock hashes, image digests, migration version, runtime policy and model configuration for each deployment. Build frontend artifacts before release and atomically switch a release symlink; restart API/worker gracefully after draining or cancelling active jobs. Never let two differently versioned workers process the same lease epoch.

Before deploying a migration back up DB consistently and immutable version store. Rollback restores compatible application release; do not downgrade a database blindly. If the schema is incompatible, restore the backup only after accounting for any commits since that backup. A workbook-level rollback is an explicit new version referencing old bytes, not deletion of history; keep this manual/admin-only in P0.

After the event export permitted evidence, revoke demo sessions/keys, remove staging and review whether to retain or destroy the VM. Powering off a VM may not stop billing; verify provider billing/retained resources and explicitly destroy unused resources after approval by the account owner.

## Production gaps

One host is a single failure domain. Real financial deployment needs defined privacy/data-processing terms, retention and backup objectives, external audit protection, stronger identity and dedicated execution capacity. The saved model catalog places selected models in US datacenters. A Stockholm VM does **not** establish EU-only inference processing. Use synthetic/redacted demo inputs; do not claim EU residency or send company data based on the VM location alone.
