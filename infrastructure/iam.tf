# IAM bindings for the ingest job service account. Purpose: grant least-privilege access
# to BigQuery (load data + run jobs), GCS staging (object admin), and Secret Manager
# (read the Postgres and BigQuery credential secrets referenced by the job).
resource "google_project_iam_member" "ingest_job_bq" {
  project = var.gcp_project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.ingest_job.email}"
}

resource "google_project_iam_member" "ingest_job_bq_job_user" {
  project = var.gcp_project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingest_job.email}"
}

resource "google_storage_bucket_iam_member" "ingest_job_staging_admin" {
  bucket = google_storage_bucket.staging.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingest_job.email}"
}

resource "google_secret_manager_secret_iam_member" "postgres_accessor" {
  project   = var.gcp_project_id
  secret_id = local.postgres_secret_short
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ingest_job.email}"
}

resource "google_secret_manager_secret_iam_member" "bigquery_accessor" {
  project   = var.gcp_project_id
  secret_id = local.bigquery_secret_short
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ingest_job.email}"
}
