# Cloud Run Job + dedicated service account for the ingest runner. Purpose: run the
# container with Secret Manager–mounted Postgres/BQ credentials, descriptor path, and GCS
# staging env vars; keeps job definition and runtime identity next to secret resolution locals.
locals {
  ingest_sa_account_id = substr(
    replace(lower("ing-${var.data_product_name}-${var.environment}"), "_", "-"),
    0,
    30
  )

  postgres_secret_short = (
    startswith(var.postgres_secret_id, "projects/")
    ? element(split("/", var.postgres_secret_id), 3)
    : var.postgres_secret_id
  )

  bigquery_secret_short = (
    startswith(var.bigquery_secret_id, "projects/")
    ? element(split("/", var.bigquery_secret_id), 3)
    : var.bigquery_secret_id
  )

  postgres_secret = (
    startswith(var.postgres_secret_id, "projects/")
    ? var.postgres_secret_id
    : "projects/${var.gcp_project_id}/secrets/${local.postgres_secret_short}"
  )

  bigquery_secret = (
    startswith(var.bigquery_secret_id, "projects/")
    ? var.bigquery_secret_id
    : "projects/${var.gcp_project_id}/secrets/${local.bigquery_secret_short}"
  )
}

resource "google_service_account" "ingest_job" {
  account_id   = local.ingest_sa_account_id
  display_name = "Ingest job (${var.data_product_name}, ${var.environment})"
  project      = var.gcp_project_id
}

resource "google_cloud_run_v2_job" "ingest" {
  name     = var.cloud_run_job_name
  location = var.gcp_region
  project  = var.gcp_project_id

  labels = local.default_labels

  template {
    template {
      service_account = google_service_account.ingest_job.email

      volumes {
        name = "postgres-creds"
        secret {
          secret       = local.postgres_secret
          default_mode = 420
          items {
            path    = "credentials"
            version = "latest"
          }
        }
      }

      volumes {
        name = "bq-creds"
        secret {
          secret       = local.bigquery_secret
          default_mode = 420
          items {
            path    = "credentials.json"
            version = "latest"
          }
        }
      }

      containers {
        image = local.image_uri

        env {
          name  = "DESCRIPTOR_PATH"
          value = var.descriptor_path
        }

        env {
          name  = "SOURCES__POSTGRES__CREDENTIALS"
          value = "/secrets/postgres/credentials"
        }

        env {
          name  = "DESTINATION__BIGQUERY__CREDENTIALS"
          value = "/secrets/bq/credentials.json"
        }

        env {
          name  = "INGEST_GCS_STAGING"
          value = "gs://${google_storage_bucket.staging.name}"
        }

        env {
          name  = "INGEST_GCP_PROJECT_ID"
          value = var.gcp_project_id
        }

        env {
          name  = "INGEST_BQ_PARTITION_FIELD"
          value = var.bq_partition_field
        }

        env {
          name  = "INGEST_BQ_CLUSTER_FIELDS"
          value = var.bq_cluster_fields_csv
        }

        env {
          name  = "INGEST_CURSOR_FIELD"
          value = var.cursor_field
        }

        env {
          name  = "INGEST_ROW_DISCRIMINATOR_COLUMN"
          value = var.row_discriminator_column
        }

        volume_mounts {
          name       = "postgres-creds"
          mount_path = "/secrets/postgres"
        }

        volume_mounts {
          name       = "bq-creds"
          mount_path = "/secrets/bq"
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
      }

      timeout     = "3600s"
      max_retries = 1
    }
  }

  depends_on = [
    google_bigquery_dataset.ingest,
    google_storage_bucket.staging,
  ]
}
