# Runbook — Restore

1. Identify the point in time (PITR window: 7 days of transaction logs, 30 daily backups).
2. Clone the Cloud SQL instance to that point: `gcloud sql instances clone lims-<env>-pg lims-restore-<date> --point-in-time <RFC3339>`
   (or restore the logical dump kept in R2 into a fresh instance).
3. Point the **staging** API at the clone by switching the `DATABASE_URL` secret version, run
   the integrity checks: row counts per tenant, `issued_document.pdf_sha256` vs the objects in
   R2, transparency log heads recompute.
4. Promote by switching the production `DATABASE_URL` secret to the clone (new Cloud Run
   revision picks it up) or discard the clone.
5. Record the evidence (counts, hashes, who approved, when) in the incident note.
