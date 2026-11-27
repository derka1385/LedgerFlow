terraform {
  required_version = ">= 1.11.0, < 2.0.0"

  required_providers {
    vultr = {
      source  = "vultr/vultr"
      version = "2.33.2"
    }
  }
}

# The provider reads VULTR_API_KEY from the operator's environment.
provider "vultr" {}
