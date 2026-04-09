# Protected path (infrastructure/core/**): immutable storage baseline for the domain.

resource "aws_s3_bucket" "raw_data" {
  bucket = "odm-${var.environment}-${var.domain_slug}-raw-data"

  tags = merge(local.tags, {
    Layer = "raw"
  })
}

resource "aws_s3_bucket" "curated_data" {
  bucket = "odm-${var.environment}-${var.domain_slug}-curated-data"

  tags = merge(local.tags, {
    Layer = "curated"
  })
}

resource "aws_s3_bucket_lifecycle_configuration" "raw_retention" {
  bucket = aws_s3_bucket.raw_data.id

  rule {
    id     = "archive-and-delete"
    status = "Enabled"

    filter {}

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = var.data_retention_days
    }
  }
}

resource "aws_glue_catalog_database" "domain" {
  name        = replace("odm_${var.environment}_${var.domain_slug}", "-", "_")
  description = "Source-aligned operational domain database (Glue metadata for curated outputs)"
  location_uri = "s3://${aws_s3_bucket.curated_data.bucket}/warehouse/"
}
