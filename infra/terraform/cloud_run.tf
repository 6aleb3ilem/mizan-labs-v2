locals {
  env_block = merge(local.common_env, {})
}

resource "google_cloud_run_v2_service" "api" {
  name     = "${local.name}-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api.email
    scaling {
      min_instance_count = var.api_min_instances
      max_instance_count = var.api_max_instances
    }
    vpc_access {
      connector = google_vpc_access_connector.sql.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
    max_instance_request_concurrency = 40
    timeout                          = "300s" # SSE streams reconnect every 5 minutes at most

    containers {
      image = var.image
      args  = ["api"]
      resources {
        limits            = { cpu = "1", memory = "1Gi" }
        cpu_idle          = true
        startup_cpu_boost = true
      }
      ports { container_port = 8080 }
      dynamic "env" {
        for_each = local.env_block
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
      startup_probe {
        http_get { path = "/health" }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 6
      }
      liveness_probe {
        http_get { path = "/health" }
        period_seconds = 30
      }
    }
  }

  # Canary: the pipeline applies with canary_percent = 10, runs the checks, then applies 100.
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = var.canary_percent
  }
  dynamic "traffic" {
    for_each = var.canary_percent < 100 ? [1] : []
    content {
      type     = "TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION"
      revision = data.google_cloud_run_v2_service.api_current.template[0].revision
      percent  = 100 - var.canary_percent
    }
  }

  depends_on = [google_secret_manager_secret_version.db_url]
}

data "google_cloud_run_v2_service" "api_current" {
  name     = "${local.name}-api"
  location = var.region
}

resource "google_cloud_run_v2_service" "worker" {
  name     = "${local.name}-worker"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.worker.email
    scaling {
      min_instance_count = var.worker_min_instances
      max_instance_count = var.worker_max_instances
    }
    vpc_access {
      connector = google_vpc_access_connector.sql.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
    containers {
      image = var.image
      args  = ["worker"]
      resources {
        limits   = { cpu = "1", memory = "2Gi" }
        cpu_idle = false # workers poll the queue; CPU always allocated
      }
      dynamic "env" {
        for_each = local.env_block
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job" "scheduler" {
  name     = "${local.name}-scheduler"
  location = var.region
  template {
    template {
      service_account = google_service_account.scheduler.email
      vpc_access {
        connector = google_vpc_access_connector.sql.id
        egress    = "PRIVATE_RANGES_ONLY"
      }
      containers {
        image = var.image
        args  = ["scheduler", "--once"]
        dynamic "env" {
          for_each = local.env_block
          content {
            name  = env.key
            value = env.value
          }
        }
        dynamic "env" {
          for_each = local.secret_env
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job" "migrate" {
  name     = "${local.name}-migrate"
  location = var.region
  template {
    template {
      service_account = google_service_account.migrator.email
      vpc_access {
        connector = google_vpc_access_connector.sql.id
        egress    = "PRIVATE_RANGES_ONLY"
      }
      containers {
        image = var.image
        args  = ["migrate"]
        dynamic "env" {
          for_each = local.env_block
          content {
            name  = env.key
            value = env.value
          }
        }
        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.db_url_migrator.secret_id
              version = "latest"
            }
          }
        }
        env {
          name = "SECRET_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.django_secret.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }
}

resource "google_cloud_scheduler_job" "tick" {
  name        = "${local.name}-tick"
  description = "Runs the periodic jobs every five minutes (digests, due/overdue, read models, transparency publish)"
  schedule    = "*/5 * * * *"
  time_zone   = "UTC"
  region      = var.region
  http_target {
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.scheduler.name}:run"
    http_method = "POST"
    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_domain_mapping" "api" {
  name     = local.api_host
  location = var.region
  metadata { namespace = var.project_id }
  spec { route_name = google_cloud_run_v2_service.api.name }
}
