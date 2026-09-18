# Secret Manager entries consumed by Cloud Run (SPEC §29.2). Values are written outside
# Terraform (CI or an operator); only the containers and their versions are declared here.

resource "google_project_service" "apis" {
  for_each = toset(var.enabled_apis)
  service  = each.value

  disable_on_destroy = false
}

resource "google_secret_manager_secret" "db_url" {
  secret_id  = "${local.name}-database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}
resource "google_secret_manager_secret_version" "db_url" {
  secret      = google_secret_manager_secret.db_url.id
  secret_data = "postgresql://${google_sql_user.app.name}:${random_password.db.result}@/${google_sql_database.app.name}?host=/cloudsql/${google_sql_database_instance.main.connection_name}"
}

resource "google_secret_manager_secret" "secret_key" {
  secret_id  = "${local.name}-secret-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}
resource "google_secret_manager_secret_version" "secret_key" {
  secret      = google_secret_manager_secret.secret_key.id
  secret_data = random_password.secret_key.result
}

resource "google_secret_manager_secret" "jwt_key" {
  secret_id  = "${local.name}-jwt-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}
resource "google_secret_manager_secret_version" "jwt_key" {
  secret      = google_secret_manager_secret.jwt_key.id
  secret_data = random_password.jwt_key.result
}

resource "google_secret_manager_secret" "storage" {
  secret_id  = "${local.name}-storage"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "smtp" {
  secret_id  = "${local.name}-smtp"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "sms" {
  secret_id  = "${local.name}-sms"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}
