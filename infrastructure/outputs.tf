# Exported identifiers after apply. Purpose: surface dataset, bucket, job name, and
# resolved image URI for scripts, GitHub Actions summaries, or operators wiring monitoring.
output "bigquery_dataset_id" {
  description = "BigQuery dataset id."
  value       = google_bigquery_dataset.ingest.dataset_id
}

output "staging_bucket_name" {
  description = "GCS staging bucket name."
  value       = google_storage_bucket.staging.name
}

output "cloud_run_job_name" {
  description = "Cloud Run Job name."
  value       = google_cloud_run_v2_job.ingest.name
}

output "artifact_image_uri" {
  description = "Resolved container image URI used by the job."
  value       = local.image_uri
}
