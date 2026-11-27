#!/bin/bash
# Executed as root by cloud-init on a fresh Ubuntu 24.04 runner.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

admin_cidr=$1

# Signed official gVisor APT repository, including its runtime sidecar files.
curl --fail --silent --show-error --location https://gvisor.dev/archive.key \
  --output /usr/share/keyrings/gvisor-archive-keyring.asc
gpg --batch --yes --dearmor \
  --output /usr/share/keyrings/gvisor-archive-keyring.gpg \
  /usr/share/keyrings/gvisor-archive-keyring.asc
printf 'deb [arch=amd64 signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main\n' \
  > /etc/apt/sources.list.d/gvisor.list
apt-get update
apt-get install --yes runsc

# Dedicated runner: all Docker invocations, including benchmark controls, use
# gVisor systrap. A missing/broken runsc fails execution, with no runc fallback.
python3 - <<'PY'
import json
from pathlib import Path
config = {
    "runtimes": {"runsc": {"path": "/usr/bin/runsc", "runtimeArgs": ["--platform=systrap"]}},
    "default-runtime": "runsc",
    "log-driver": "local",
    "log-opts": {"max-size": "10m", "max-file": "2"},
}
Path('/etc/docker').mkdir(exist_ok=True)
Path('/etc/docker/daemon.json').write_text(json.dumps(config, indent=2) + '\n')
PY
systemctl enable docker
systemctl restart docker

# Only the human deploy operator uses sudo Docker; no API/worker socket access.
python3 -m venv /opt/ledgerflow-tools
/opt/ledgerflow-tools/bin/pip install --disable-pip-version-check 'uv==0.11.17'
ln -sf /opt/ledgerflow-tools/bin/uv /usr/local/bin/uv
install -d -o deploy -g deploy -m 0750 /srv/ledgerflow

ufw default deny incoming
ufw default allow outgoing
ufw allow from "$admin_cidr" to any port 22 proto tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
/usr/sbin/sshd -t
systemctl reload ssh

# Capture actual installed versions; package repositories are rolling inputs.
install -d -m 0700 /var/lib/ledgerflow
{
  date --utc --iso-8601=seconds
  dpkg-query -W docker.io runsc
  runsc --version
  docker info --format '{{json .Runtimes}} {{.DefaultRuntime}}'
  uv --version
} > /var/lib/ledgerflow/bootstrap-versions.txt
touch /var/lib/ledgerflow/bootstrap-complete
