terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "core" {
  source = "./core"

  environment           = var.environment
  domain_slug           = var.domain_slug
  data_owner            = var.data_owner
  data_retention_days   = var.data_retention_days
  enable_pii_masking    = var.enable_pii_masking
}
