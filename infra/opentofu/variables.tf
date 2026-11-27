variable "region" {
  description = "Vultr region; confirm live capacity before applying."
  type        = string
  default     = "sto"
}

variable "plan" {
  description = "Vultr VM plan (candidate: 4 vCPU / 8 GiB)."
  type        = string
  default     = "vc2-4c-8gb"
}

variable "os_id" {
  description = "Vultr Ubuntu 24.04 LTS x64 catalog ID; recheck before applying."
  type        = number
  default     = 2284
}

variable "name" {
  description = "VM hostname and resource label prefix."
  type        = string
  default     = "ledgerflow-1"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,61}[a-z0-9]$", var.name))
    error_message = "Use a lowercase hostname, 2–63 characters, ending in a letter or digit."
  }
}

variable "ssh_public_key" {
  description = "Operator's single-line OpenSSH Ed25519 PUBLIC key."
  type        = string

  validation {
    condition     = can(regex("^ssh-ed25519 [A-Za-z0-9+/]+={0,3}( [^\r\n]+)?$", var.ssh_public_key))
    error_message = "Provide a single-line ssh-ed25519 public key, never a private key."
  }
}

variable "ssh_admin_cidr" {
  description = "Operator's public IPv4 address as an explicit /32."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.ssh_admin_cidr)) && can(regex("/32$", var.ssh_admin_cidr))
    error_message = "SSH must be restricted to one valid IPv4 /32, e.g. 203.0.113.10/32."
  }
}
