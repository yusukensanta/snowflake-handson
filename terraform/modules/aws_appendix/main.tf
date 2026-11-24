# OPTIONAL APPENDIX. Never applied by the repo owner (no AWS account); validate-only.
# Pattern: Snowflake storage integration -> IAM role trusting Snowflake's IAM user (+ external ID) -> external volume.
terraform {
  required_providers {
    snowflake = { source = "snowflakedb/snowflake", version = "2.23.0" }
    aws       = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

variable "bucket_name" { type = string }
variable "role_name" {
  type    = string
  default = "snowflake-handson-iceberg"
}

resource "aws_s3_bucket" "lake" { bucket = var.bucket_name }

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" }
  }
}

# Two-step trust: first apply with a placeholder principal, then read
# DESC EXTERNAL VOLUME to get Snowflake's IAM user + external ID and set these variables.
variable "snowflake_iam_user_arn" {
  type    = string
  default = ""
}
variable "snowflake_external_id" {
  type    = string
  default = ""
}

data "aws_iam_policy_document" "trust" {
  count = var.snowflake_iam_user_arn == "" ? 0 : 1
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = [var.snowflake_iam_user_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [var.snowflake_external_id]
    }
  }
}

resource "aws_iam_role" "snowflake" {
  count              = var.snowflake_iam_user_arn == "" ? 0 : 1
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.trust[0].json
}

data "aws_iam_policy_document" "access" {
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:GetObjectVersion"]
    resources = ["${aws_s3_bucket.lake.arn}/*"]
  }
  statement {
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.lake.arn]
  }
}

resource "aws_iam_role_policy" "access" {
  count  = var.snowflake_iam_user_arn == "" ? 0 : 1
  role   = aws_iam_role.snowflake[0].id
  policy = data.aws_iam_policy_document.access.json
}

resource "snowflake_execute" "external_volume" {
  execute = <<-SQL
    CREATE EXTERNAL VOLUME IF NOT EXISTS HANBIT_LAKE_VOL STORAGE_LOCATIONS = ((
      NAME = 'ap-northeast-2' STORAGE_PROVIDER = 'S3' STORAGE_BASE_URL = 's3://${aws_s3_bucket.lake.bucket}/'
      STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::<ACCOUNT_ID>:role/${var.role_name}'))
  SQL
  revert  = "DROP EXTERNAL VOLUME IF EXISTS HANBIT_LAKE_VOL"
}
