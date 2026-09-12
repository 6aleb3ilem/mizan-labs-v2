resource "google_service_account" "api" {
  account_id   = "${local.name}-api"
  display_name = "Mizan API (${var.environment})"
}

resource "google_service_account" "worker" {
  account_id   = "${local.name}-worker"
  display_name = "Mizan worker (${var.environment})"
}

resource "google_service_account" "scheduler" {
  account_id   = "${local.name}-scheduler"
  display_name = "Mizan scheduler (${var.environment})"
}

resource "google_service_account" "migrator" {
  account_id   = "${local.name}-migrator"
  display_name = "Mizan migrations (${var.environment})"
}

resource "google_service_account" "deployer" {
  account_id   = "${local.name}-deployer"
  display_name = "GitHub Actions deployer (${var.environment})"
}

resource "google_project_iam_member" "deployer_roles" {
  for_each = toset(["roles/run.admin", "roles/iam.serviceAccountUser", "roles/artifactregistry.writer", "roles/cloudsql.client"])
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.deployer.email}"
}

# Cloud Scheduler invokes the scheduler job through its own identity.
resource "google_cloud_run_v2_job_iam_member" "scheduler_invoker" {
  name     = google_cloud_run_v2_job.scheduler.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

# The API is public behind Cloudflare; the worker never receives HTTP traffic.
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
