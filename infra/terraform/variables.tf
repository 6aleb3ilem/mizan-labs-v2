variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "europe-west1"
}
variable "environment" {
  type        = string
  description = "staging | production"
}
variable "image" {
  type        = string
  description = "Full image reference built by CI, e.g. europe-west1-docker.pkg.dev/<project>/mizan/platform:<sha>"
}
variable "domain" {
  type        = string
  description = "Apex domain managed in Cloudflare, e.g. mizanlabs.mr"
}
variable "cloudflare_account_id" { type = string }
variable "cloudflare_zone_id" { type = string }
variable "cloudflare_api_token" {
  type      = string
  sensitive = true
}
variable "r2_endpoint" {
  type        = string
  description = "S3 endpoint of the Cloudflare R2 bucket (https://<account>.r2.cloudflarestorage.com)"
}
variable "r2_access_key_id" {
  type      = string
  sensitive = true
}
variable "r2_secret_access_key" {
  type      = string
  sensitive = true
}
variable "db_tier" {
  type    = string
  default = "db-custom-2-8192"
}
variable "api_min_instances" {
  type    = number
  default = 1
}
variable "api_max_instances" {
  type    = number
  default = 10
}
variable "worker_min_instances" {
  type    = number
  default = 1
}
variable "worker_max_instances" {
  type    = number
  default = 5
}
variable "canary_percent" {
  type        = number
  default     = 100
  description = "Traffic share of the latest revision; the deploy pipeline sets 10 then 100"
}
variable "smtp_host" {
  type    = string
  default = ""
}
variable "smtp_user" {
  type    = string
  default = ""
}
variable "smtp_password" {
  type      = string
  sensitive = true
  default   = ""
}
variable "tsa_url" {
  type    = string
  default = ""
}

locals {
  name         = "lims-${var.environment}"
  api_host     = "api.${var.domain}"
  app_host     = "app.${var.domain}"
  admin_host   = "admin.${var.domain}"
  portal_host  = "client.${var.domain}"
  verify_host  = "verify.${var.domain}"
  spa_projects = {
    "back-office" = local.app_host
    "admin"       = local.admin_host
    "portal"      = local.portal_host
    "verify"      = local.verify_host
  }
  common_env = {
    MIZAN_ENV            = var.environment
    ALLOWED_HOSTS        = local.api_host
    CORS_ALLOWED_ORIGINS = join(",", [for h in values(local.spa_projects) : "https://${h}"])
    VERIFY_BASE_URL      = "https://${local.verify_host}"
    PORTAL_BASE_URL      = "https://${local.portal_host}"
    APP_BASE_URL         = "https://${local.app_host}"
    ADMIN_BASE_URL       = "https://${local.admin_host}"
    STORAGE_BACKEND      = "s3"
    S3_ENDPOINT_URL      = var.r2_endpoint
    S3_BUCKET_DOCUMENTS  = cloudflare_r2_bucket.documents.name
    S3_BUCKET_ATTACHMENTS = cloudflare_r2_bucket.attachments.name
    SIGNING_BACKEND      = "kms"
    KMS_KEY_RING         = google_kms_key_ring.signing.id
    EMAIL_HOST           = var.smtp_host
    EMAIL_HOST_USER      = var.smtp_user
    EMAIL_USE_TLS        = "true"
    TSA_URL              = var.tsa_url
    LOG_JSON             = "true"
    CONN_MAX_AGE         = "0"
  }
  secret_env = {
    DATABASE_URL         = google_secret_manager_secret.db_url.secret_id
    SECRET_KEY           = google_secret_manager_secret.django_secret.secret_id
    S3_ACCESS_KEY_ID     = google_secret_manager_secret.r2_key.secret_id
    S3_SECRET_ACCESS_KEY = google_secret_manager_secret.r2_secret.secret_id
    EMAIL_HOST_PASSWORD  = google_secret_manager_secret.smtp_password.secret_id
  }
}
