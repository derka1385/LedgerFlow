resource "vultr_ssh_key" "operator" {
  name    = "${var.name}-operator"
  ssh_key = var.ssh_public_key
}

resource "vultr_firewall_group" "runner" {
  description = "${var.name}: HTTPS/HTTP public; SSH operator only"
}

resource "vultr_firewall_rule" "ssh" {
  firewall_group_id = vultr_firewall_group.runner.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = cidrhost(var.ssh_admin_cidr, 0)
  subnet_size       = 32
  port              = "22"
  notes             = "Operator SSH only"
}

resource "vultr_firewall_rule" "web" {
  for_each = toset(["80", "443"])

  firewall_group_id = vultr_firewall_group.runner.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = "0.0.0.0"
  subnet_size       = 0
  port              = each.value
  notes             = "Public web entrypoint"
}

locals {
  # Vultr's provider encodes user_data itself. Pass raw cloud-config, not base64.
  cloud_config = {
    package_update  = true
    package_upgrade = true
    ssh_pwauth      = false
    disable_root    = true
    users = [{
      name                = "deploy"
      shell               = "/bin/bash"
      lock_passwd         = true
      sudo                = ["ALL=(ALL) NOPASSWD:ALL"]
      ssh_authorized_keys = [var.ssh_public_key]
    }]
    packages = ["ca-certificates", "caddy", "curl", "gnupg", "docker.io", "python3.12-venv", "ufw"]
    write_files = [
      {
        path        = "/usr/local/sbin/ledgerflow-bootstrap"
        permissions = "0700"
        owner       = "root:root"
        content     = file("${path.module}/bootstrap.sh")
      },
      {
        path        = "/etc/ssh/sshd_config.d/00-ledgerflow.conf"
        permissions = "0644"
        owner       = "root:root"
        content     = "PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\n"
      }
    ]
    runcmd = [["bash", "/usr/local/sbin/ledgerflow-bootstrap", var.ssh_admin_cidr]]
  }
}

resource "vultr_instance" "runner" {
  region            = var.region
  plan              = var.plan
  os_id             = var.os_id
  label             = var.name
  hostname          = var.name
  ssh_key_ids       = [vultr_ssh_key.operator.id]
  firewall_group_id = vultr_firewall_group.runner.id
  enable_ipv6       = false
  backups           = "disabled"
  activation_email  = false
  tags              = ["ledgerflow", "jury-demo"]
  user_data         = "#cloud-config\n${yamlencode(local.cloud_config)}"

  # Ensure the VM is never created before its inbound rules are installed.
  depends_on = [vultr_firewall_rule.ssh, vultr_firewall_rule.web]
}
