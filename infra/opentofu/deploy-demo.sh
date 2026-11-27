#!/bin/bash
# Run from the operator's Mac after the approved OpenTofu apply.
set -euo pipefail
umask 077
root=$(cd "$(dirname "$0")/../.." && pwd)
tofu_bin=${TOFU_BIN:-tofu}
module="$root/infra/opentofu"
ip=$("$tofu_bin" -chdir="$module" output -raw ipv4_address)
host=$("$tofu_bin" -chdir="$module" output -raw public_hostname)
remote="deploy@$ip"
[[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ && $host =~ ^[a-z0-9.-]+$ ]] || exit 2
work=$(mktemp -d)
remote_work=
trap 'rm -rf "$work"; if [ -n "$remote_work" ]; then ssh "$remote" "rm -rf -- $remote_work" || true; fi' EXIT

# Keep any existing local demo bundle intact. The clean build is isolated.
mkdir -p "$work/ui"
for item in src public index.html package.json package-lock.json tsconfig.json vite.config.ts; do
  cp -R "$root/frontend/$item" "$work/ui/"
done
(cd "$work/ui" && npm ci --no-audit --no-fund && npm run build)

# Package only the runtime, public assets and synthetic fixtures.
mkdir -p "$work/release/frontend" "$work/release/fixtures" "$work/release/config" \
  "$work/release/demo" "$work/release/benchmark/results" "$work/release/infra/opentofu"
cp "$root"/{pyproject.toml,uv.lock} "$work/release/"
cp -R "$root/landing" "$root/accounting" "$root/ledgerflow" "$work/release/"
cp -R "$root/frontend/dev-mock-api" "$work/release/frontend/"
cp -R "$work/ui/dist" "$work/release/frontend/"
cp -R "$root/fixtures/synthetic" "$work/release/fixtures/"
cp "$root"/config/{inference.json,fx_rates.json} "$work/release/config/"
cp "$root/demo/containment_demo.py" "$work/release/demo/"
cp "$root/benchmark/results/kpis.json" "$work/release/benchmark/results/"
cp "$module"/{check-runtime.sh,install-demo.sh,ledgerflow-demo.service} "$work/release/infra/opentofu/"
COPYFILE_DISABLE=1 tar --no-xattrs --exclude=__pycache__ --exclude=.DS_Store --exclude=.pytest_cache \
  -C "$work/release" -czf "$work/release.tar.gz" .

# Verify the host key out of band before the first connection.
ssh "$remote" 'sudo cloud-init status --wait && sudo test -f /var/lib/ledgerflow/bootstrap-complete'
created=$(ssh "$remote" 'mktemp -d /tmp/ledgerflow-release.XXXXXX')
[[ $created =~ ^/tmp/ledgerflow-release\.[[:alnum:]]+$ ]] || exit 2
remote_work=$created
ssh "$remote" "tar -xzf - -C $remote_work" < "$work/release.tar.gz"

# The Python producer sends only the key through the SSH channel. It never prints
# the key to the terminal, adds it to the archive, or puts it in a process argument.
python3 - "$root/.env" <<'PY' | ssh "$remote" "sudo -n bash $remote_work/infra/opentofu/install-demo.sh $remote_work $host"
import os
from pathlib import Path
import sys

key = os.environ.get("VULTR_INFERENCE_API_KEY", "")
path = Path(sys.argv[1])
if not key and path.is_file():
    for line in path.read_text().splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "VULTR_INFERENCE_API_KEY":
            key = value.strip().strip('"').strip("'")
            break
if not key or "\r" in key or "\n" in key:
    sys.exit("Set VULTR_INFERENCE_API_KEY locally before deploying.")
sys.stdout.write(key + "\n")
PY
printf 'Expected demo endpoint: https://%s/welcome/\n' "$host"
