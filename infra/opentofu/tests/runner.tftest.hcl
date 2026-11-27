mock_provider "vultr" {}

variables {
  ssh_admin_cidr = "203.0.113.10/32"
  ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA test-only"
}

run "restricted_runner_plan" {
  command = plan

  assert {
    condition     = vultr_instance.runner.region == "sto" && vultr_instance.runner.plan == "vc2-4c-8gb" && vultr_instance.runner.os_id == 2284
    error_message = "Runner must default to the reviewed Stockholm / 8 GiB / Ubuntu configuration."
  }

  assert {
    condition     = vultr_firewall_rule.ssh.subnet == "203.0.113.10" && vultr_firewall_rule.ssh.subnet_size == 32 && vultr_firewall_rule.ssh.port == "22"
    error_message = "SSH must allow only the operator /32."
  }

  assert {
    condition     = toset(keys(vultr_firewall_rule.web)) == toset(["80", "443"]) && !vultr_instance.runner.enable_ipv6
    error_message = "Expose only HTTP/HTTPS publicly and leave IPv6 disabled until separately configured."
  }

  assert {
    condition     = !local.cloud_config.ssh_pwauth && local.cloud_config.disable_root && local.cloud_config.users[0].name == "deploy"
    error_message = "Bootstrap must create a key-only deploy user and disable root SSH."
  }

  assert {
    condition     = startswith(vultr_instance.runner.user_data, "#cloud-config\n") && local.cloud_config.runcmd[0][2] == "203.0.113.10/32"
    error_message = "Send raw cloud-config with the same restricted host firewall source."
  }
}

run "reject_public_ssh" {
  command = plan

  variables {
    ssh_admin_cidr = "0.0.0.0/0"
  }

  expect_failures = [var.ssh_admin_cidr]
}

run "reject_ipv6_without_matching_policy" {
  command = plan

  variables {
    ssh_admin_cidr = "2001:db8::1/128"
  }

  expect_failures = [var.ssh_admin_cidr]
}

run "reject_private_key_input" {
  command = plan

  variables {
    ssh_public_key = "-----BEGIN OPENSSH PRIVATE KEY-----"
  }

  expect_failures = [var.ssh_public_key]
}
