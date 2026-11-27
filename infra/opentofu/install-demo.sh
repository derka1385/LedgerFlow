#!/bin/bash
# Runs as root on the dedicated VM. Read the inference key from stdin only.
set -euo pipefail
set +x
umask 077
bundle=$1
host=$2
[[ $host =~ ^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]*[a-z0-9]$ ]] || exit 2
read -r key
# EnvironmentFile is line-oriented. A Vultr API key uses an unquoted token.
[[ $key =~ ^[A-Za-z0-9._~+/=-]+$ ]] || { echo "Invalid inference key format." >&2; exit 1; }
test -f /var/lib/ledgerflow/bootstrap-complete
bash "$bundle/infra/opentofu/check-runtime.sh"

release=$(mktemp -d /srv/ledgerflow/releases/build.XXXXXX)
cp -R "$bundle"/. "$release/"
uv --directory "$release" sync --frozen --no-dev --no-install-project --python /usr/bin/python3.12
chmod -R a+rX "$release"
chown -R root:root "$release"
test -f "$release/frontend/dist/index.html"
test -f "$release/landing/index.html"

install -d -m 0700 /etc/ledgerflow
secret=$(mktemp /etc/ledgerflow/.demo.env.XXXXXX)
trap 'rm -f "$secret"' EXIT
printf 'VULTR_INFERENCE_API_KEY=%s\n' "$key" > "$secret"
unset key
chmod 0600 "$secret"

# The public site serves static media with HEAD and range support outside Python.
cat >/etc/caddy/ledgerflow.new <<CADDY
{
  acme_ca https://acme-v02.api.letsencrypt.org/directory
}

$host {
  header {
    Permissions-Policy "camera=(self)"
    X-Content-Type-Options "nosniff"
  }
  redir /welcome /welcome/ 308
  handle_path /welcome/* {
    root * /srv/ledgerflow/current/landing
    file_server
  }
  handle {
    reverse_proxy 127.0.0.1:8790
  }
}
CADDY
chown root:caddy /etc/caddy/ledgerflow.new
chmod 0640 /etc/caddy/ledgerflow.new
runuser -u caddy -- caddy validate --adapter caddyfile --config /etc/caddy/ledgerflow.new

install -m 0755 "$release/infra/opentofu/check-runtime.sh" /usr/local/sbin/ledgerflow-check-runtime
install -m 0644 "$release/infra/opentofu/ledgerflow-demo.service" /etc/systemd/system/ledgerflow-demo.service
unit_overrides=/etc/systemd/system/ledgerflow-demo.service.d
install -d -m 0755 "$unit_overrides"
printf '[Service]\nEnvironment=LEDGERFLOW_PUBLIC_ORIGIN=https://%s\n' "$host" > "$unit_overrides/origin.conf"
chmod 0644 "$unit_overrides/origin.conf"
mv -f "$secret" /etc/ledgerflow/demo.env
next=$(mktemp -d /srv/ledgerflow/deploy.XXXXXX)
ln -s "$release" "$next/current"
mv -Tf "$next/current" /srv/ledgerflow/current
rmdir "$next"
systemctl daemon-reload
systemctl enable ledgerflow-demo
systemctl restart ledgerflow-demo
for attempt in $(seq 1 20); do
  if curl --fail --silent --max-time 2 http://127.0.0.1:8790/api/v1/health/live >/dev/null; then
    mv -f /etc/caddy/ledgerflow.new /etc/caddy/Caddyfile
    systemctl enable caddy
    systemctl restart caddy
    exit 0
  fi
  sleep 1
done
echo "LedgerFlow did not become ready on loopback." >&2
exit 1
