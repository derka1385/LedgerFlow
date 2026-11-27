#!/bin/bash
set -euo pipefail
umask 077
root=$(cd "$(dirname "$0")/../.." && pwd)
tofu_bin=${TOFU_BIN:-tofu}
module="$root/infra/opentofu"
ip=$("$tofu_bin" -chdir="$module" output -raw ipv4_address)
remote="deploy@$ip"
url=$("$tofu_bin" -chdir="$module" output -raw jury_url)
origin=${url%/welcome/}
out="$root/demo/vultr_evidence"
mkdir -p "$out"

# Let public TLS finish provisioning, then require a trusted HTTP 200.
curl --fail --silent --show-error --retry 24 --retry-delay 5 --retry-connrefused --retry-all-errors \
  --retry-max-time 130 --max-time 10 --head "$url" | tee "$out/https.txt"
grep -Eq '^HTTP/[^ ]+ 200([[:space:]]|$)' "$out/https.txt"
{
  printf 'Verified at (UTC): %s\nURL: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$url"
  printf 'Instance: %s\nRegion: %s\n' "$("$tofu_bin" -chdir="$module" output -raw instance_id)" "$("$tofu_bin" -chdir="$module" output -raw region)"
  ssh "$remote" 'sudo cat /var/lib/ledgerflow/bootstrap-versions.txt &&
    sudo -n runuser -u ledgerflow -g docker -- /usr/local/sbin/ledgerflow-check-runtime &&
    curl -fsS http://127.0.0.1:8790/api/v1/health/live'
  printf '\n'
} | tee "$out/host.txt"
ssh "$remote" 'cd /srv/ledgerflow/current && sudo -n runuser -u ledgerflow -g docker -- env TMPDIR=/var/lib/ledgerflow-demo .venv/bin/python demo/containment_demo.py' \
  | tee "$out/containment.txt"
grep -qx 'RESULT: CONTAINED' "$out/containment.txt"
BASE="$origin" OUT="$out/desktop" node "$root/film/jury_flow.mjs" desktop | tee "$out/jury-desktop.txt"
SAMPLE=2 BASE="$origin" OUT="$out/android" node "$root/film/jury_flow.mjs" android | tee "$out/jury-android.txt"
