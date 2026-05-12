# Primary GCP resources shared by the ingest job: BigQuery dataset, GCS staging bucket,
# shared labels, and the resolved Artifact Registry image URI. Purpose: host the data
# landing zone and container image reference that Cloud Run will use at runtime.
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

locals {
  default_labels = merge(
    {
      data_product = var.data_product_name
      environment  = var.environment
      managed_by   = "terraform"
    },
    var.labels
  )

  image_uri = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${var.artifact_registry_repository}/${var.image_name}:${var.image_tag}"
}

resource "google_bigquery_dataset" "ingest" {
  dataset_id                 = var.bq_dataset_id
  project                    = var.gcp_project_id
  location                   = var.gcp_region
  delete_contents_on_destroy = var.environment == "dev"

  labels = local.default_labels
}

resource "google_storage_bucket" "staging" {
  name                        = var.gcs_staging_bucket
  project                     = var.gcp_project_id
  location                    = var.gcp_region
  uniform_bucket_level_access = true
  force_destroy               = var.environment == "dev"

  labels = local.default_labels
}
