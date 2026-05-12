# Terraform core configuration: minimum engine version, GCS remote state backend block
# (actual bucket/prefix supplied at init), and the Google provider pin. Purpose: lock tooling
# and provider APIs so applies stay reproducible across machines and CI.
terraform {
  required_version = ">= 1.5.0"

  backend "gcs" {}

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.40.0, < 7.0.0"
    }
  }
}
