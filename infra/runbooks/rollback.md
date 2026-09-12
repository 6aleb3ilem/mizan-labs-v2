# Runbook — Rollback

1. In Cloud Run, shift 100 % of the traffic of `lims-<env>-api` to the previous revision:
   `gcloud run services update-traffic lims-<env>-api --region <region> --to-revisions <previous>=100`
   (seconds; no rebuild). Do the same for the worker if the release changed task code.
2. Do not roll back the database: migrations are backward compatible. A reverting migration,
   if needed, ships in the next release.
3. Re-run the k6 smoke test; confirm the error rate in Grafana.
4. Open an incident note with the failing revision, the symptom and the next steps.
