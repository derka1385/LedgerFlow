# LedgerFlow Vultr runner — OpenTofu

This module manages one VM, one SSH-key registration, one firewall group, and
three inbound IPv4 rules. Defaults: Stockholm (`sto`), `vc2-4c-8gb`, Ubuntu 24.04
x64 (`os_id = 2284`). Check current catalog availability/pricing before apply;
the handoff's USD 40/month is a catalog observation, not a guaranteed quote.

**Status:** validated locally with OpenTofu 1.13.10 and Vultr provider 2.33.2;
four mocked-plan tests passed. No authenticated plan/apply, VM bootstrap, or
Vultr containment measurement has been performed. Mocked plans validate policy
and resource schemas, not provider capacity or runtime enforcement.

## What gets configured

- SSH on TCP 22 from one explicitly supplied IPv4 `/32`.
- Public TCP 80/443; IPv6 disabled. No Docker API or application-development ports.
- Key-only `deploy` user with operator sudo access; root/password SSH disabled.
- Ubuntu Docker package and official signed gVisor APT repository.
- Docker default runtime `runsc`, with `--platform=systrap`; no silent runc fallback.
- Host UFW rules matching the cloud firewall, plus bounded daemon log rotation.
- Python venv tools, `uv` 0.11.17, and `/srv/ledgerflow` for reviewed source.
- Actual installed versions at `/var/lib/ledgerflow/bootstrap-versions.txt`.

The deploy operator has root-equivalent sudo privileges. Application/worker users
are not given Docker access. Bootstrap does not start the development mock API,
install a reverse proxy, configure DNS/TLS, or deploy an application service.
Public 80/443 rules reserve those entrypoints; no listener is created here.

gVisor packages and Ubuntu updates are fetched at first boot, so bootstrap is not
a reproducible immutable image build. Record installed versions and image digests
with every measurement. Compatibility of gVisor, tmpfs options, Excel processing,
and the complete containment profile must be measured on the resulting VM.

## Configure and plan

Install OpenTofu 1.13.10. Run these commands from the **repository root**:

```sh
export VULTR_API_KEY   # supply through your shell/secret environment first
export TF_VAR_ssh_admin_cidr='YOUR_PUBLIC_IPV4/32'
export TF_VAR_ssh_public_key="$(ssh-keygen -y -f "$HOME/.ssh/id_ed25519")"
umask 077

tofu -chdir=infra/opentofu init -lockfile=readonly
tofu -chdir=infra/opentofu plan -out=runner.tfplan
tofu -chdir=infra/opentofu apply runner.tfplan
```

Only the derived public key reaches the configuration. Never supply an account
key, inference key, private SSH key, or repository access token in variables,
cloud-init, or user data. The provider consumes `VULTR_API_KEY` directly from the
operator's environment. `terraform.tfvars.example` shows the variable format if
you prefer a local ignored `terraform.tfvars` file.

The module uses local state. State and saved plans are git-ignored, but can contain
Vultr-generated passwords and infrastructure metadata. Keep them private and
retain state for updates/destruction. Only one operator should apply at a time;
use a team-controlled encrypted, locking remote backend before shared operation.
Do not upload state/plans as CI artifacts. The provider lock file is included
with this module and should be committed alongside the templates.

Vultr's Terraform provider takes **raw** `user_data` and base64-encodes it internally;
this differs from constructing the REST request yourself. Cloud-init runs on first
boot: updating `user_data` on an existing instance is not a configuration-management
run. For bootstrap changes, rebuild the disposable runner with an explicit reviewed
`-replace=vultr_instance.runner` plan, after exporting evidence you want to keep.

## Wait for bootstrap and verify runtime

```sh
HOST="deploy@$(tofu -chdir=infra/opentofu output -raw ipv4_address)"
INSTANCE_ID="$(tofu -chdir=infra/opentofu output -raw instance_id)"
ssh "$HOST" 'sudo cloud-init status --wait --long'
ssh "$HOST" 'sudo test -f /var/lib/ledgerflow/bootstrap-complete'
ssh "$HOST" 'sudo cat /var/lib/ledgerflow/bootstrap-versions.txt'
ssh "$HOST" 'sudo docker info --format "{{.DefaultRuntime}}"'
```

Expected default runtime: `runsc`. A Terraform apply completing does not mean
cloud-init succeeded. If bootstrapping fails, inspect
`sudo journalctl -u cloud-final` and `/var/log/cloud-init-output.log` over SSH.
Verify the SSH host-key fingerprint through the Vultr console on first connection.

## Transfer reviewed source and measure

First commit the intended source, including `uv.lock`; the archive below contains
only that commit, and avoids copying local secrets/private workbooks to the VM.
Choose the reviewed commit hash rather than assuming the current checkout is it.

```sh
RELEASE='REPLACE_WITH_REVIEWED_COMMIT_HASH'
git archive --format=tar "$RELEASE" | ssh "$HOST" 'tar -xf - -C /srv/ledgerflow'
ssh "$HOST" 'uv --directory /srv/ledgerflow sync --frozen --extra dev --python 3.12'
ssh "$HOST" 'uv --directory /srv/ledgerflow run --frozen --extra dev python benchmark/corpus.py'
ssh "$HOST" 'sudo docker pull python:3.12-slim'
```

The tag pull is a discovery step. Inspect its `RepoDigests`, choose the vetted
digest, and use that exact digest for the measurement:

```sh
ssh "$HOST" 'sudo docker image inspect python:3.12-slim --format "{{json .RepoDigests}}"'
```

In an SSH session on the VM, from `/srv/ledgerflow`:

```sh
export LEDGERFLOW_SANDBOX_IMAGE='python@sha256:REPLACE_WITH_VETTED_DIGEST'
export PYTHONPATH='frontend/dev-mock-api:accounting:benchmark'
sudo env LEDGERFLOW_SANDBOX_IMAGE="$LEDGERFLOW_SANDBOX_IMAGE" PYTHONPATH="$PYTHONPATH" \
  .venv/bin/python -m pytest -ra frontend/dev-mock-api/test_sandbox.py \
  frontend/dev-mock-api/test_mock_api.py frontend/dev-mock-api/test_vsi_integration.py
sudo env LEDGERFLOW_SANDBOX_IMAGE="$LEDGERFLOW_SANDBOX_IMAGE" PYTHONPATH="$PYTHONPATH" \
  .venv/bin/python benchmark/security_evidence.py \
  --host-label vultr-REPLACE_WITH_INSTANCE_ID \
  --output /srv/ledgerflow/security-evidence.vultr.json
```

Reject skipped required runtime tests. Pair the JSON with `INSTANCE_ID`, the
console's region/OS identity, bootstrap versions, and a terminal recording.
Archive the reviewed release hash alongside the evidence. The evidence host label
is operator-supplied, not provider attestation. See
[`docs/SANDBOX_REVIEW.md`](../../docs/SANDBOX_REVIEW.md) for remaining runner gaps.

## Validate without credentials

```sh
tofu -chdir=infra/opentofu fmt -check -recursive
tofu -chdir=infra/opentofu init -backend=false -input=false -lockfile=readonly
tofu -chdir=infra/opentofu validate
tofu -chdir=infra/opentofu test
bash -n infra/opentofu/bootstrap.sh
```

GitHub Actions runs these checks with a mocked provider and no cloud credentials.
Tests cover the default VM shape, restricted SSH, expected public ports,
key-only bootstrap, raw cloud-config, and rejection of public/IPv6 SSH and
private-key input. The HCL uses Terraform-compatible constructs; the checked
toolchain and lock file target OpenTofu. Terraform uses a different default
provider registry, so initialize/lock separately if switching tools.

## Destroy the disposable runner

Export evidence first, then destroy from the same state directory:

```sh
tofu -chdir=infra/opentofu plan -destroy -out=destroy.tfplan
tofu -chdir=infra/opentofu apply destroy.tfplan
```

This removes the module's VM, firewall, and SSH-key registration. A halted VM may
remain billable; verify deletion in the Vultr console.

## Kubernetes / Helm scope

This repository currently targets a single runner VM. Kubernetes would require
VKE provisioning, workload identities, persistent storage, ingress/TLS, and an
explicit `RuntimeClass` installed/configured on every execution node. Sandboxes
would need separate Jobs with `runAsNonRoot`, dropped capabilities,
`readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, default seccomp,
network-deny policy, deadlines, and enforced storage limits. An `emptyDir.sizeLimit`
on its own is not a replacement for a demonstrated kernel-enforced quota.

The current runner invokes a local Docker daemon; simply wrapping the API in a
Deployment or mounting the node's Docker socket would not implement that design.
Helm can package a future Kubernetes backend once this execution model exists.

## Verified implementation sources

- [Vultr instance resource](https://github.com/vultr/terraform-provider-vultr/blob/v2.33.2/website/docs/r/instance.html.markdown)
- [Vultr firewall rule](https://github.com/vultr/terraform-provider-vultr/blob/v2.33.2/website/docs/r/firewall_rule.html.markdown)
- [Vultr SSH key](https://github.com/vultr/terraform-provider-vultr/blob/v2.33.2/website/docs/r/ssh_key.html.markdown)
- [Provider user-data encoding](https://github.com/vultr/terraform-provider-vultr/blob/v2.33.2/vultr/resource_vultr_instance.go)
- [gVisor installation](https://gvisor.dev/docs/user_guide/install/)
