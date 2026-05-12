# Input variables for the ingest stack. Purpose: declare every value Terraform needs
# (GCP project, dataset, secrets, image coordinates, job name) so CI and operators pass
# a single consistent contract—typically aligned with the instantiated blueprint manifest.
variable "environment" {
  type        = string
  description = "Single deployment target name (must match a manifest environments[] entry and descriptor lifecycleInfo key)."
}

variable "gcp_project_id" {
  type        = string
  description = "GCP project ID."
}

variable "gcp_region" {
  type        = string
  description = "Region for BigQuery, GCS, and Cloud Run."
}

variable "data_product_name" {
  type        = string
  description = "Machine-readable data product name (resource naming)."
}

variable "gcs_staging_bucket" {
  type        = string
  description = "GCS bucket name for dlt staging (globally unique)."
}

variable "bq_dataset_id" {
  type        = string
  description = "BigQuery dataset ID (must match output port promises.api.definition.schema.databaseSchemaName in the descriptor)."
}

variable "bq_partition_field" {
  type        = string
  description = "BigQuery partition column for the target table (runtime env INGEST_BQ_PARTITION_FIELD; not stored in descriptor table.definition)."
}

variable "bq_cluster_fields_csv" {
  type        = string
  description = "Comma-separated BigQuery clustering columns (runtime env INGEST_BQ_CLUSTER_FIELDS)."
}

variable "cursor_field" {
  type        = string
  description = "Optional incremental cursor column name for Postgres extract (runtime env INGEST_CURSOR_FIELD; empty for full snapshots)."
  default     = ""
}

variable "row_discriminator_column" {
  type        = string
  description = "Column name injected on each row with the source Postgres schema (runtime env INGEST_ROW_DISCRIMINATOR_COLUMN)."
}

variable "postgres_secret_id" {
  type        = string
  description = "Secret Manager secret id for PostgreSQL credentials."
}

variable "bigquery_secret_id" {
  type        = string
  description = "Secret Manager secret id for BigQuery service account JSON."
}

variable "artifact_registry_repository" {
  type        = string
  description = "Artifact Registry repository id."
}

variable "image_name" {
  type        = string
  description = "Container image name segment under the Artifact Registry repo (without registry host)."
  default     = "ingest-runner"
}

variable "image_tag" {
  type        = string
  description = "Container image tag or digest (set by CI)."
  default     = "latest"
}

variable "cloud_run_job_name" {
  type        = string
  description = "Cloud Run Job resource name (DNS-compliant; typically dpName + environment)."
}

variable "descriptor_path" {
  type        = string
  description = "Path to data product descriptor inside the container."
  default     = "/app/descriptor/data-product-descriptor.json"
}

variable "labels" {
  type        = map(string)
  description = "Labels applied to created resources."
  default     = {}
}
