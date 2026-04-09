# Protected: baseline IAM — narrow roles for ingest, transform, and read-only consumers.

data "aws_iam_role" "central_governance" {
  name = "example-lakeformation-central-admin"
}

resource "aws_iam_role" "ingest_raw" {
  name = "${local.name_prefix}-ingest-raw"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "glue.amazonaws.com"
      }
    }]
  })

  tags = local.tags
}

resource "aws_iam_role" "dlt_transform" {
  name = "${local.name_prefix}-dlt-transform"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        AWS = data.aws_iam_role.central_governance.arn
      }
    }]
  })

  tags = local.tags
}
