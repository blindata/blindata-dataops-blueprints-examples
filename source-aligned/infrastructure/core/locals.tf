locals {
  name_prefix = "odm-${var.environment}-${var.domain_slug}"
  tags = {
    Domain      = var.domain_slug
    Environment = var.environment
    Owner       = var.data_owner
    ManagedBy   = "OpenDataMesh-Blueprint"
  }
}
