resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = "${var.name_prefix}-run-sa"
  display_name = "DNS Self-Service Cloud Run runtime identity (${var.environment})"
}

# Lets the runtime SA write structured logs to Cloud Logging (Logs Explorer).
resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}
