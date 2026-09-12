resource "random_password" "django_secret" {
  length = 64
}

locals {
  db_url_app      = "postgresql://${google_sql_user.app.name}:${random_password.app_db.result}@${google_sql_database_instance.pg.private_ip_address}:5432/${google_sql_database.mizan.name}"
  db_url_migrator = "postgresql://${google_sql_user.migrator.name}:${random_password.migrator_db.result}@${google_sql_database_instance.pg.private_ip_address}:5432/${google_sql_database.mizan.name}"
}

resource "google_secret_manager_secret" "db_url" {
  secret_id  = "${local.name}-database-url"
  replication { auto {} }
  depends_on = [google_project_service.apis]
}
resource "google_secret_manager_secret_version" "db_url" {
  secret      = google_secret_manager_secret.db_url.id
  secret_data = local.db_url_app
}

resource "google_secret_manager_secret" "db_url_migrator" {
  secret_id  = "${local.name}-database-url-migrator"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "db_url_migrator" {
  secret      = google_secret_manager_secret.db_url_migrator.id
  secret_data = local.db_url_migrator
}

resource "google_secret_manager_secret" "django_secret" {
  secret_id  = "${local.name}-secret-key"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "django_secret" {
  secret      = google_secret_manager_secret.django_secret.id
  secret_data = random_password.django_secret.result
}

resource "google_secret_manager_secret" "r2_key" {
  secret_id  = "${local.name}-r2-access-key"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "r2_key" {
  secret      = google_secret_manager_secret.r2_key.id
  secret_data = var.r2_access_key_id
}

resource "google_secret_manager_secret" "r2_secret" {
  secret_id  = "${local.name}-r2-secret-key"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "r2_secret" {
  secret      = google_secret_manager_secret.r2_secret.id
  secret_data = var.r2_secret_access_key
}

resource "google_secret_manager_secret" "smtp_password" {
  secret_id  = "${local.name}-smtp-password"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "smtp_password" {
  secret      = google_secret_manager_secret.smtp_password.id
  secret_data = var.smtp_password == "" ? "unset" : var.smtp_password
}

resource "google_secret_manager_secret_iam_member" "runtime_access" {
  for_each = {
    for pair in setproduct(
      ["db_url", "django_secret", "r2_key", "r2_secret", "smtp_password"],
      [google_service_account.api.email, google_service_account.worker.email, google_service_account.scheduler.email],
    ) : "${pair[0]}-${pair[1]}" => pair
  }
  secret_id = {
    db_url        = google_secret_manager_secret.db_url.id
    django_secret = google_secret_manager_secret.django_secret.id
    r2_key        = google_secret_manager_secret.r2_key.id
    r2_secret     = google_secret_manager_secret.r2_secret.id
    smtp_password = google_secret_manager_secret.smtp_password.id
  }[each.value[0]]
  role   = "roles/secretmanager.secretAccessor"
  member = "serviceAccount:${each.value[1]}"
}

resource "google_secret_manager_secret_iam_member" "migrator_access" {
  for_each  = toset([google_secret_manager_secret.db_url_migrator.id, google_secret_manager_secret.django_secret.id])
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.migrator.email}"
}
