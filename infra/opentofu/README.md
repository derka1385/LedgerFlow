# LedgerFlow jury demo on Vultr

OpenTofu manages a disposable Ubuntu 24.04 VM in Stockholm by default. The
`vc2-2c-4gb` plan has 2 vCPU and 4 GiB. Vultr's public catalog lists USD 20/month.
At the published 672-hour cap this is about USD 0.030/hour, excluding inference
and applicable taxes. Confirm the exact rate in the Vultr console before apply.
[Billing details](https://docs.vultr.com/support/platform/billing/how-am-i-billed-for-my-servers)

Cloud-init installs Python 3.12, Docker, gVisor and Caddy. Docker defaults to
`runsc` with systrap. The host and cloud firewalls allow TCP 80/443 publicly and
SSH from the operator's IPv4 /32. Caddy serves the landing and proxies the API
and application to `127.0.0.1:8790`.

The browser demo is a shared synthetic workspace. The service seeds the sample
workbook at startup and stores the shared demo session in memory. Restarting
clears the demo runs. The host service can control Docker; receipt-generated
programs never receive the Docker socket or the inference key.

## 1. Review the plan

From the repository root, supply the **account** key in your shell and set
`TF_VAR_ssh_admin_cidr` to your public IPv4 /32. The SSH variable is a public key.
Use an existing Ed25519 key whose private counterpart you can use from this Mac.

```sh
umask 077
export VULTR_API_KEY
export TF_VAR_ssh_admin_cidr='YOUR_PUBLIC_IPV4/32'
export TF_VAR_ssh_public_key="$(cat ~/.ssh/id_ed25519.pub)"

tofu -chdir=infra/opentofu init -lockfile=readonly
tofu -chdir=infra/opentofu plan -out=jury.tfplan
```

If you own a DNS name for the demo, set `TF_VAR_public_hostname` before planning
and point its A record to the VM after apply. Otherwise the stack uses
`<public-ip>.sslip.io`, which resolves to the VM. Caddy requests a public
Let's Encrypt certificate. [Caddy HTTPS requirements](https://caddyserver.com/docs/automatic-https)

After reviewing the exact plan and approving the hourly cost:

```sh
tofu -chdir=infra/opentofu apply jury.tfplan
```

Keep local state and plans private. They may contain Vultr-generated credentials
and are ignored by Git. Keep the state until the instance has been destroyed.

## 2. Deploy and verify before switching the jury link

Verify the new VM's SSH host-key fingerprint using the Vultr console before the
first connection. Set `VULTR_INFERENCE_API_KEY` in the local shell environment or
the repository's ignored `.env`. The deploy command builds the frontend in a
temporary directory and uploads only the runtime, landing and synthetic
fixtures. It streams the inference credential separately through SSH into the
root-owned 0600 environment file on the VM.

```sh
bash infra/opentofu/deploy-demo.sh
bash infra/opentofu/verify-demo.sh
```

The verification command checks trusted HTTPS, the actual VM's runtime and
container image, the containment result from the VM, and the two Playwright
jury flows. It saves the results to `demo/vultr_evidence/`. The camera test uses
a simulated device in Chrome. A failure in Docker, gVisor or inference is a
deployment failure. Keep the existing jury link active until these checks pass.

After passing, update `landing/index.html` in the working tree and the public
checkout with the validated HTTPS origin in the `ledgerflow-app` meta tag.
Replace the temporary jury link in the public README, push the reviewed files,
and verify that GitHub Pages opens the new workspace and creates a session.
Record the results in `DEMO_EVIDENCE.md`, `FINAL_RELEASE_CHECKLIST.md` and
`film/VERIFICATION_REPORT.md` before retiring the temporary tunnel.

## 3. Destroy after the evaluation

Archive the verified evidence first, then use the same OpenTofu state directory:

```sh
tofu -chdir=infra/opentofu destroy
```

Destroy removes the VM, firewall and SSH-key registration managed by this stack.
Powering off the VM leaves it billable.

## Local validation

```sh
tofu -chdir=infra/opentofu fmt -check -recursive
tofu -chdir=infra/opentofu validate
tofu -chdir=infra/opentofu test
for script in infra/opentofu/*.sh; do bash -n "$script"; done
```

Mocked OpenTofu tests verify the configuration and firewall plan. They do not
exercise an authenticated apply, cloud-init on Vultr, or container enforcement
on that VM.
