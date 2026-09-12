resource "google_sql_database_instance" "pg" {
  name             = "${local.name}-pg"
  database_version = "POSTGRES_16"
  region           = var.region
  depends_on       = [google_service_networking_connection.private_vpc]

  settings {
    tier              = var.db_tier
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings { retained_backups = 30 }
    }
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }
    database_flags {
      name  = "max_connections"
      value = "200"
    }
    insights_config {
      query_insights_enabled = true
    }
  }
  deletion_protection = var.environment == "production"
}

resource "google_sql_database" "mizan" {
  name     = "mizan"
  instance = google_sql_database_instance.pg.name
}

resource "random_password" "app_db" {
  length  = 32
  special = false
}

resource "random_password" "migrator_db" {
  length  = 32
  special = false
}

# The application role is subject to row-level security (SPEC §27.6); migrations use a privileged role.
resource "google_sql_user" "app" {
  name     = "mizan_app"
  instance = google_sql_database_instance.pg.name
  password = random_password.app_db.result
}

resource "google_sql_user" "migrator" {
  name     = "mizan_migrator"
  instance = google_sql_database_instance.pg.name
  password = random_password.migrator_db.result
}
