output "api_url" { value = google_cloud_run_v2_service.api.uri }
output "api_host" { value = local.api_host }
output "spa_hosts" { value = local.spa_projects }
output "sql_instance" { value = google_sql_database_instance.pg.connection_name }
output "kms_key_ring" { value = google_kms_key_ring.signing.id }
output "migrate_job" { value = google_cloud_run_v2_job.migrate.name }
output "scheduler_job" { value = google_cloud_run_v2_job.scheduler.name }
output "deployer_service_account" { value = google_service_account.deployer.email }
