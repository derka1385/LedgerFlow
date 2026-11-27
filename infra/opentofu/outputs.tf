output "instance_id" {
  description = "Vultr instance identity to pair with containment evidence."
  value       = vultr_instance.runner.id
}

output "ipv4_address" {
  value = vultr_instance.runner.main_ip
}

output "ssh_command" {
  value = "ssh deploy@${vultr_instance.runner.main_ip}"
}

output "firewall_group_id" {
  value = vultr_firewall_group.runner.id
}

output "region" {
  value = vultr_instance.runner.region
}

output "public_hostname" {
  value = var.public_hostname != "" ? var.public_hostname : "${vultr_instance.runner.main_ip}.sslip.io"
}

output "jury_url" {
  description = "Expected HTTPS demo URL once Caddy and the application are verified."
  value       = "https://${var.public_hostname != "" ? var.public_hostname : "${vultr_instance.runner.main_ip}.sslip.io"}/welcome/"
}
