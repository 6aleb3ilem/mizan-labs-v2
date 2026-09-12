# Infrastructure (Terraform)

One environment per workspace directory: Cloud Run services `api` and `worker`, Cloud Run
jobs `scheduler` (ticked every five minutes by Cloud Scheduler) and `migrate`, Cloud SQL for
PostgreSQL 16 (private IP, PITR), Cloud KMS signing keys (PDF seal RSA-3072/HSM, QR Ed25519),
Secret Manager, Cloudflare R2 buckets, Cloudflare Pages projects and DNS for the four SPAs,
and a WAF rate limit on the verification digest endpoint (SPEC §27, Appendix Q).

```
terraform init -backend-config=environments/staging.backend.hcl
terraform plan  -var-file=environments/staging.tfvars -var image=<image> -var canary_percent=10
terraform apply -var-file=environments/staging.tfvars -var image=<image> -var canary_percent=10
gcloud run jobs execute lims-staging-migrate --region europe-west1 --wait
# automated checks (k6 smoke, /ready) then:
terraform apply -var-file=environments/staging.tfvars -var image=<image> -var canary_percent=100
```

Secrets (`cloudflare_api_token`, `r2_access_key_id`, `r2_secret_access_key`, `smtp_password`)
come from the CI secret store, never from tfvars files. The example tfvars are committed;
real `*.tfvars` are ignored by git.

Two database roles exist: `mizan_app` (subject to row-level security; used by api, worker and
scheduler) and `mizan_migrator` (owner; used by the migrate job only). The first migration
creates the extensions and policies; see `backend/mizan/platform/db/rls.py`.
