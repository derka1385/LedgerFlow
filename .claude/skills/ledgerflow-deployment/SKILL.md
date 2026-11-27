---
name: ledgerflow-deployment
description: >-
  Deploy, inspect, update, verify, or tear down this LedgerFlow project's
  single-VM Vultr OpenTofu runner stack. Use for LedgerFlow Vultr deployment,
  tofu plan/apply, cloud-init or SSH troubleshooting, sandbox containment and
  Excel verification on the VM, or deployment evidence collection. Scoped to
  this repository; do not apply to unrelated infrastructure or general cloud questions.
compatibility: OpenTofu, Git, OpenSSH, and shell access; provisioning requires VULTR_API_KEY in the operator environment.
---

# LedgerFlow deployment

Operate the existing single-VM stack in `infra/opentofu`. Keep this skill in the
repository; do not install or synchronize it into global skills directories.

## Read the implementation first

Resolve the repository root, then read these files as needed:

1. [DEPLOYMENT.md](../../../DEPLOYMENT.md) — operator workflow and commands.
2. [Module README](../../../infra/opentofu/README.md) — infrastructure details.
3. `infra/opentofu/{versions,variables,main,outputs}.tf` and `bootstrap.sh` — actual
   resources, defaults, inputs, outputs, and first-boot behavior.
4. [Sandbox review](../../../docs/SANDBOX_REVIEW.md),
   `frontend/dev-mock-api/sandbox.py`, and `benchmark/security_evidence.py` —
   runtime policy, evidence generation, and verification limitations.
5. [Application deployment design](../../../docs/VULTR_DEPLOYMENT.md) — consult
   when the task extends to application processes, DNS, HTTPS, or service identities.

Treat executable configuration as the source of truth when documentation differs.
Report the discrepancy and update the relevant guide when changing implementation.

## Establish scope and inputs

- Inspect Git status before editing. Preserve concurrent/unfamiliar changes.
- Identify whether the user wants validation/planning, provisioning, host diagnosis,
  verification, replacement, or teardown. A request for documentation or a plan
  does not authorize applying resources.
- Locate existing stack state and deployed VM identity before creating anything.
  Reuse the intended state; a fresh state can create duplicate resources.
- For provisioning, check that `VULTR_API_KEY` is set without printing its value.
  Ask the user to supply it through the operator environment if missing. Do not
  search unrelated folders, logs, or shell history for credentials.
- Obtain the public Ed25519 key, operator's actual public IPv4 `/32`, intended
  release commit, and the state location. Ask for any missing or ambiguous input
  rather than guessing an address, key, commit, or target VM.
- Read region/plan/OS defaults from `variables.tf`; verify current catalog/capacity
  for a real apply. Do not silently substitute a different region, size, or OS.
- Keep infrastructure credentials local. This workflow needs no inference key,
  GitHub token, or private SSH key inside cloud-init or on the runner.

## Validate and plan

Run from the repository root, adapting only to the installed OpenTofu executable:

```sh
tofu -chdir=infra/opentofu fmt -check -recursive
tofu -chdir=infra/opentofu init -backend=false -input=false -lockfile=readonly
tofu -chdir=infra/opentofu validate
tofu -chdir=infra/opentofu test
bash -n infra/opentofu/bootstrap.sh
```

Mocked plans establish schema and configuration behavior, not cloud readiness.
For provisioning, use the state-aware init/plan/apply sequence in `DEPLOYMENT.md`.
Inspect the saved plan for unexpected changes before applying. The initial stack
currently has six resources: VM, SSH key, firewall group, and three inbound rules.
Avoid automatic approval flags and keep state/plans out of Git and evidence bundles.

The Vultr provider accepts raw `user_data` and base64-encodes it internally.
Preserve the provider lock file and the restricted SSH/firewall policy.

## Provision and inspect bootstrap

After an authorized apply:

1. Obtain instance ID, region, and public IPv4 from the actual outputs.
2. Connect as `deploy`, verifying the SSH host key using the Vultr console.
3. Wait for successful `cloud-init status --wait --long` and verify
   `/var/lib/ledgerflow/bootstrap-complete`.
4. Capture `/var/lib/ledgerflow/bootstrap-versions.txt` and actual Docker/runsc versions.
5. Confirm Docker's default runtime is `runsc` and inspect its `systrap` configuration.
6. Inspect host and cloud firewall rules. No public Docker API or development port
   is part of this stack.

Bootstrap failure is a deployment failure even if OpenTofu apply succeeded.
Diagnose cloud-init/systemd logs and runtime configuration; do not hide a failure
by changing the default runtime to `runc` or disabling resource restrictions.

The deploy operator has sudo privileges. Keep application identities outside the
Docker group and without the runtime socket. The stack prepares a runner; it does
not create a public production app, Caddy configuration, DNS/TLS, or Kubernetes cluster.

## Transfer source and verify on the actual host

Follow the release-transfer commands in `DEPLOYMENT.md`:

- Use a reviewed committed release containing `uv.lock` and the evidence tools.
  Explain that `git archive` excludes uncommitted changes. Commit/push only when requested.
- Transfer to a fresh release directory and install frozen dependencies with `uv`.
  Generate synthetic benchmark receipts; do not copy private source workbooks or secrets.
- Inspect the execution image and select its exact vetted repository digest.
- Run the real-runtime pytest suite and retain JUnit results. Reject empty suites,
  skipped required runtime tests, failures, and errors.
- Run `benchmark/security_evidence.py` with the actual Vultr instance ID in the
  host label. Require all 13 containment cases, a working positive network control,
  cleanup evidence, storage/temp-isolation checks, legitimate Excel execution,
  and workbook preservation.
- Inspect raw observations in addition to the aggregate `passed` flag. The evidence
  collector currently gives its nested pytest invocation 30 seconds; a timeout or
  missing output is not a successful measurement.

Record actual work/tmpfs capacities, inodes, memory/swap, privileges, networking,
runtime, and image identity. A caught `ENOSPC` demonstrates a storage allocation
limit, not immediate termination. Synthetic Excel checks do not establish support
for all workbooks or native Excel recalculation.

Export raw JSON, JUnit results, installed versions, release hash, host identity,
and instance/region records. Pair the operator-supplied host label with Vultr
console evidence. Exclude credentials and state/plans from shared evidence.

## Updates, recovery, and teardown

- Cloud-init is first-boot configuration: changing `user_data` does not rerun it.
  For a requested rebuild, export evidence and inspect an explicit replacement plan.
- After replacement, refresh IP/instance outputs and verify the new SSH host key.
- A changed operator IP needs both cloud-firewall and host-UFW updates. Keep a
  working recovery session until the new source address can connect.
- An archive overlay leaves deleted files behind; use clean release directories
  for updates. Do not invent a production-service rollout or migration protocol.
- For requested teardown, export evidence, use the same state to plan/apply destroy,
  and verify cloud resource deletion. Halted VMs can remain billable.
- Ask before deleting data/state, switching the intended target/environment, or
  adopting a new deployment architecture when the user's request does not specify it.

## Report results

Give a concise handoff with:

1. Actions performed and the exact stack, release, instance ID, and region.
2. Measured results, including executed/passed/skipped counts and evidence paths.
3. Remaining blockers and the specific input or next action needed.

Distinguish **template validation**, **provisioned**, **bootstrap verified**,
**containment measured**, and **public application deployed**. Claim each only
after observing its own evidence. If credentials, tooling, or VM access are missing,
complete independent local validation and report the blocker without inventing results.
