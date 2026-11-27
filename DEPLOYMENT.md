# Deploy LedgerFlow's sandbox runner on Vultr with OpenTofu

This guide deploys the **single-VM runner stack** in [`infra/opentofu`](infra/opentofu/).
Here, “stack” means one OpenTofu root module and its state, not a Kubernetes
cluster or a separate multi-stack orchestration service.

For coding agents, the repository-local
[LedgerFlow deployment skill](.claude/skills/ledgerflow-deployment/SKILL.md)
captures this workflow and its verification requirements.

The path is: **configure Vultr credentials → validate/plan → provision → verify
cloud-init → transfer a reviewed release → run containment and Excel checks →
export evidence → destroy when finished**.

**Verification status:** the module has passed local schema validation and four
mocked-plan tests with OpenTofu 1.13.10 and Vultr provider 2.33.2. Authenticated
provisioning, first-boot configuration, and 13/13 containment on Vultr have not
been established. Follow the gates below before publishing deployment claims.

## 1. Stack contents and boundaries

| Component | Configuration |
|---|---|
| VM | `ledgerflow-1`, Stockholm `sto`, `vc2-4c-8gb`, Ubuntu 24.04 x64 (`os_id = 2284`) |
| SSH | Public-key registration; key-only `deploy` user with sudo; root/password SSH disabled |
| Cloud firewall | TCP 22 from your public IPv4 `/32`; public TCP 80/443; IPv6 disabled |
| Host firewall | UFW with matching inbound rules; outgoing traffic allowed for installation and host operations |
| Execution runtime | Docker with gVisor `runsc` as the default, using `systrap` |
| Tooling | Git, Python venv support, `uv` 0.11.17; source directory `/srv/ledgerflow` |
| Bootstrap evidence | Installed versions and completion marker under `/var/lib/ledgerflow` |

The default plan was previously listed at **USD 40/month**; verify current price,
availability, and account limits in [Vultr](https://console.vultr.com/) before
applying. The template disables paid automatic backups.

This stack prepares the execution host. It does not start a public LedgerFlow
application, configure DNS, or install HTTPS/reverse-proxy services. Open ports
80/443 do not imply a web service is running. Application/service deployment is
described as a separate design in [`docs/VULTR_DEPLOYMENT.md`](docs/VULTR_DEPLOYMENT.md).
The development mock API must not be treated as a production service.

## 2. Local prerequisites

On your operator workstation, install:

- [OpenTofu](https://opentofu.org/docs/intro/install/), preferably **1.13.10**, the
  locally validated version. The module accepts `>= 1.11.0, < 2.0.0`.
- Git and OpenSSH (`ssh`, `ssh-keygen`, `scp`).
- An Ed25519 SSH key you control. The default examples use `~/.ssh/id_ed25519`.

Run local commands from the repository root unless a section says **on the VM**.
Keep the same terminal session so its variables remain available.

The stack files are:

```text
infra/opentofu/
  versions.tf                  # provider and tool version constraints
  variables.tf                 # region, plan, OS, hostname, public key, admin /32
  main.tf                      # VM, SSH key, firewall, cloud-config
  outputs.tf                   # instance ID, IPv4, SSH command, firewall ID, region
  bootstrap.sh                 # first-boot Docker/gVisor and host setup
  .terraform.lock.hcl           # selected provider and checksums
  terraform.tfvars.example     # example non-secret configuration
  tests/runner.tftest.hcl       # credential-free mocked-plan tests
```

Retain the provider lock file with the configuration. Installation follows rolling
Ubuntu and gVisor repositories; record actual installed versions for each release.

## 3. Enable the Vultr infrastructure API

1. Sign in to [the Vultr console](https://console.vultr.com/).
2. Open **Account → API** and enable access. The account settings may also be
   available at [API settings](https://my.vultr.com/settings/#settingsapi).
3. Generate/copy the infrastructure API key.
4. Restrict API access to the public IP of the workstation making the requests.
   If you use a VPN, use its current public exit IP.

In **macOS zsh**, enter the key without displaying it or placing its value in
command history:

```zsh
read -rs "VULTR_API_KEY?Paste Vultr infrastructure API key: "
print
export VULTR_API_KEY
[[ -n "$VULTR_API_KEY" ]] && print "Vultr API key is set"
```

The provider reads `VULTR_API_KEY` directly. Do not put it in Git, `.tfvars`,
cloud-init, or the VM. The separate `VULTR_INFERENCE_API_KEY` is not needed for
provisioning or these containment tests. An environment variable in this terminal
is not automatically available to an already-running agent or another terminal.

## 4. Configure the stack

Replace the example address with your workstation's **actual public IPv4**:

```sh
export TF_VAR_ssh_admin_cidr='YOUR_PUBLIC_IPV4/32'
export TF_VAR_ssh_public_key="$(ssh-keygen -y -f "$HOME/.ssh/id_ed25519")"
export TF_VAR_region='sto'
export TF_VAR_plan='vc2-4c-8gb'
export TF_VAR_os_id='2284'
export TF_VAR_name='ledgerflow-1'
umask 077
```

`ssh-keygen -y` derives the public key locally; the private key stays on your
workstation. It may ask for the key's passphrase. Use `ssh -i PATH` / `scp -i PATH`
later if you use a key other than the default.

The module requires one IPv4 `/32` for SSH. Recheck the region, plan and OS IDs
against the current catalog before apply. To use a local variables file instead,
copy `infra/opentofu/terraform.tfvars.example` to `terraform.tfvars` in that same
directory and replace its placeholders. `TF_VAR_*` environment values are used
when no higher-precedence variable file or command-line value overrides them.

### State ownership

This stack uses local state under `infra/opentofu`. Its `.gitignore` excludes
`.terraform/`, state files, saved plans, local `.tfvars`, and crash logs. State and
plans can contain generated passwords and sensitive infrastructure information;
keep them private and preserve the state until teardown is complete. Do not
publish them with jury evidence or CI artifacts.

Use one operator/state owner for this deployment. A shared deployment needs a
configured encrypted remote backend with locking; that backend is not supplied
by this module. Starting from a second empty state may create duplicate resources.

## 5. Validate, plan, and provision

These checks initialize the provider and validate the template; mocked tests make
no cloud changes:

```sh
tofu -chdir=infra/opentofu fmt -check -recursive
tofu -chdir=infra/opentofu init -input=false -lockfile=readonly
tofu -chdir=infra/opentofu validate
tofu -chdir=infra/opentofu test
bash -n infra/opentofu/bootstrap.sh
```

Create and inspect the real plan, then apply it:

```sh
tofu -chdir=infra/opentofu plan -out=runner.tfplan
tofu -chdir=infra/opentofu show runner.tfplan
tofu -chdir=infra/opentofu apply runner.tfplan

HOST="deploy@$(tofu -chdir=infra/opentofu output -raw ipv4_address)"
INSTANCE_ID="$(tofu -chdir=infra/opentofu output -raw instance_id)"
tofu -chdir=infra/opentofu output
```

A first deployment should create **six resources**: one VM, one SSH key, one
firewall group, one SSH rule, and two web rules. Confirm the plan has the intended
region, size, OS, key and source `/32`. The VM depends on the firewall rules.

Applying starts billable infrastructure. Provider readiness does not establish
cloud-init completion or working containment. The provider accepts **raw**
cloud-config as `user_data` and encodes it internally; do not base64-encode the
module's value again.

## 6. Verify SSH, bootstrap, and gVisor

Allow a few minutes for first boot. Verify the SSH host-key fingerprint using the
Vultr console on the first connection; do not disable host-key checking.

```sh
ssh "$HOST" 'sudo cloud-init status --wait --long'
ssh "$HOST" 'sudo test -f /var/lib/ledgerflow/bootstrap-complete'
ssh "$HOST" 'sudo cat /var/lib/ledgerflow/bootstrap-versions.txt'
ssh "$HOST" 'sudo docker info --format "{{.DefaultRuntime}}"'
ssh "$HOST" 'sudo runsc --version'
ssh "$HOST" 'sudo ufw status verbose'
```

Require successful cloud-init, the completion marker, default runtime **`runsc`**,
and SSH limited to your configured address. The bootstrap configures `systrap`
without requiring nested KVM. Runtime compatibility still requires the tests below.

The `deploy` identity is a privileged operator through sudo. Application/worker
identities must not be added to the Docker group or given the Docker socket.

## 7. Transfer a reviewed release

Choose a committed release containing the infrastructure, Python lock file,
runner, and test tools. Uncommitted working-tree files are not included by
`git archive`. Before transfer:

```sh
RELEASE='REPLACE_WITH_REVIEWED_COMMIT_HASH'
git rev-parse --verify "$RELEASE^{commit}"
git cat-file -e "${RELEASE}:uv.lock"
git cat-file -e "${RELEASE}:benchmark/security_evidence.py"
git cat-file -e "${RELEASE}:infra/opentofu/main.tf"
```

For the **fresh VM's empty `/srv/ledgerflow` directory**:

```sh
set -o pipefail
git archive --format=tar "$RELEASE" | ssh "$HOST" 'tar -xf - -C /srv/ledgerflow'
ssh "$HOST" 'uv --directory /srv/ledgerflow sync --frozen --extra dev --python 3.12'
ssh "$HOST" 'uv --directory /srv/ledgerflow run --frozen --extra dev python benchmark/corpus.py'
ssh "$HOST" 'sudo docker pull python:3.12-slim'
ssh "$HOST" 'sudo docker image inspect python:3.12-slim --format "{{json .RepoDigests}}"'
```

This transfer needs no GitHub credential on the VM. Review committed content
before archiving; Git tracking is not a secret scanner. Private workbooks and
local credentials should remain outside the release.

The image tag is a discovery step. Select the vetted `python@sha256:…` repository
digest from inspection and use it for the measurement. Do not publish a run as
reproducible using only a mutable tag.

## 8. Execute containment and Excel checks

Open an SSH session with `ssh "$HOST"`. Run this section **on the VM**:

```sh
cd /srv/ledgerflow
export LEDGERFLOW_SANDBOX_IMAGE='python@sha256:REPLACE_WITH_VETTED_DIGEST'
export PYTHONPATH='frontend/dev-mock-api:accounting:benchmark'
export INSTANCE_ID='REPLACE_WITH_INSTANCE_ID_FROM_LOCAL_TOFU_OUTPUT'
install -d -m 0700 artifacts/deployment

sudo env LEDGERFLOW_SANDBOX_IMAGE="$LEDGERFLOW_SANDBOX_IMAGE" PYTHONPATH="$PYTHONPATH" \
  .venv/bin/python -m pytest -ra --tb=short \
  frontend/dev-mock-api/test_sandbox.py \
  frontend/dev-mock-api/test_mock_api.py \
  frontend/dev-mock-api/test_vsi_integration.py \
  --junitxml=artifacts/deployment/runtime-tests.xml
```

Continue only if that command succeeds. Reject a missing, empty, skipped, failed,
or errored required runtime suite:

```sh
.venv/bin/python - <<'PY'
import xml.etree.ElementTree as ET
cases = ET.parse('artifacts/deployment/runtime-tests.xml').getroot().findall('.//testcase')
assert cases, 'No runtime tests executed'
bad = [case.get('name') for case in cases
       if any(case.find(tag) is not None for tag in ('skipped', 'failure', 'error'))]
assert not bad, f'Required runtime checks did not pass: {bad}'
print(f'All {len(cases)} required runtime tests passed')
PY

sudo env LEDGERFLOW_SANDBOX_IMAGE="$LEDGERFLOW_SANDBOX_IMAGE" PYTHONPATH="$PYTHONPATH" \
  .venv/bin/python benchmark/security_evidence.py \
  --host-label "vultr-$INSTANCE_ID" \
  --output artifacts/deployment/security-evidence.vultr.json
```

Require the evidence command to complete successfully. Inspect the raw JSON for:

- **13/13 containment probes**, including explicit quota exhaustion in P13.
- A successful **network-positive control**; unreachable controls do not prove egress isolation.
- Container removal and the actual live mounts, resource settings and runtime.
- Storage/inode/temp-isolation regressions and successful legitimate Excel execution.
- Workbook preservation, image identity, timestamps and source hashes.

The current runner requests 128 MiB/4,096 inodes for `/work`, with Python temp
files in the same budget and a separate 1 MiB `/dev/shm`. A caught `ENOSPC` is
storage containment; it does not mean the program was immediately killed.
These settings need actual host evidence. Synthetic Excel checks do not prove
compatibility with every workbook or native Excel recalculation. The tests use
scripted/mock inference and make no live inference-performance claim.

The evidence script's aggregate flag is not sufficient alone: review the runtime
test results and filesystem observation too. See the independent
[sandbox review](docs/SANDBOX_REVIEW.md) for known lifecycle and collector limitations.

## 9. Export evidence

Still **on the VM**, add host identity and installed versions:

```sh
uname -a > artifacts/deployment/host.txt
cat /etc/os-release >> artifacts/deployment/host.txt
printf '%s\n' "$INSTANCE_ID" > artifacts/deployment/instance-id.txt
sudo cat /var/lib/ledgerflow/bootstrap-versions.txt > artifacts/deployment/bootstrap-versions.txt
sudo chown -R deploy:deploy artifacts/deployment
tar -czf /home/deploy/ledgerflow-evidence.tgz -C /srv/ledgerflow/artifacts deployment
```

Run `exit` to leave the SSH session and return to the **original workstation
terminal**, where `HOST`, `RELEASE` and your OpenTofu environment are still set.
Create a private evidence directory and fetch the bundle:

```sh
mkdir -p artifacts/vultr-evidence
scp "${HOST}:/home/deploy/ledgerflow-evidence.tgz" artifacts/vultr-evidence/
git rev-parse "$RELEASE^{commit}" > artifacts/vultr-evidence/release-commit.txt
tofu -chdir=infra/opentofu output -raw instance_id > artifacts/vultr-evidence/instance-id.txt
tofu -chdir=infra/opentofu output -raw region > artifacts/vultr-evidence/region.txt
```

Pair this bundle with the Vultr console's instance/region/OS record and a terminal
recording of the run. The JSON host label is operator-supplied, not provider
attestation. Review paths and host metadata before sharing. Keep state, plans,
API keys and provider-generated passwords out of the jury bundle.

## 10. Updates, troubleshooting, and teardown

### Updates

- Keep using the same module and state for infrastructure changes; review each plan.
- Cloud-init runs on first boot. Changing `user_data` does not rerun bootstrap.
  To rebuild this disposable host, export evidence first, then plan an explicit replacement:

  ```sh
  tofu -chdir=infra/opentofu plan -replace=vultr_instance.runner -out=replace.tfplan
  tofu -chdir=infra/opentofu apply replace.tfplan
  ```

  Re-read `HOST` and `INSTANCE_ID` from outputs afterward; the IP and host key can change.
- If your public IP changes, updating the cloud rule alone does not update UFW.
  From the still-authorized connection or Vultr console, permit the new `/32` in
  UFW, update `TF_VAR_ssh_admin_cidr` and apply, verify a new SSH connection, then
  remove the old UFW rule. Avoid closing your recovery session prematurely.
- For application source updates, use a new clean release directory and recreate
  its environment. Overlaying a tar archive on an old release leaves deleted files
  behind; the transfer command above is for first installation.

### Common failures

| Symptom | Check |
|---|---|
| API rejects requests | Key is exported in this terminal; API access enabled; allowlisted public IP matches VPN/NAT exit |
| Plan/OS unavailable | Current Vultr catalog, Stockholm capacity, account quotas; update inputs deliberately |
| SSH times out | VM readiness, actual `/32`, cloud firewall, UFW and recovery-console access |
| `deploy` user not ready | Allow cloud-init to create it; use the console to inspect boot progress |
| Cloud-init fails | `sudo journalctl -u cloud-final`; `/var/log/cloud-init-output.log`; APT/network errors |
| Default runtime is not `runsc` | `/etc/docker/daemon.json`, installed `runsc`, Docker service logs; stop verification until corrected |
| Sandbox errors or skipped tests | Exact image exists under sudo Docker; `PYTHONPATH` set; source/lock included; inspect raw stderr |
| Network-positive control fails | Host-gateway routing, gVisor and host firewall may block the control listener; diagnose without accepting a containment pass |
| No evidence file / timeout | Preserve terminal output; inspect the failing command. The evidence script currently bounds its nested pytest invocation to 30 seconds |
| Missing private workbook tests | Only synthetic fixtures are shipped; obtain separate approved compatibility evidence for private workbooks |

### Teardown

After exporting evidence, run locally from the same state directory:

```sh
tofu -chdir=infra/opentofu plan -destroy -out=destroy.tfplan
tofu -chdir=infra/opentofu show destroy.tfplan
tofu -chdir=infra/opentofu apply destroy.tfplan
unset VULTR_API_KEY
```

This destroys the module's VM, firewall/rules and SSH-key registration. Verify the
resources are gone in the Vultr console. Stopping a VM is not equivalent to
destroying it and may not stop billing. Retain the reviewed source, evidence and
private state records according to your retention needs.

## Related documentation

- [OpenTofu module details and source references](infra/opentofu/README.md)
- [Broader application deployment design](docs/VULTR_DEPLOYMENT.md)
- [Security policy](docs/SECURITY.md)
- [Independent sandbox review and verification limits](docs/SANDBOX_REVIEW.md)
- [Test plan](docs/TEST_PLAN.md)
- [OpenTofu CLI](https://opentofu.org/docs/cli/)
