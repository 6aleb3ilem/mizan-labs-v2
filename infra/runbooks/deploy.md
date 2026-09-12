# Runbook — Deploy

1. Merge to `main`. The pipeline (`.github/workflows/ci.yml`) runs lint, type checks, the backend
   suite with PostgreSQL (RLS and authorisation matrix tests), the front-end suites and builds
   the container image tagged with the commit SHA.
2. `deploy.yml` deploys staging automatically: `terraform apply` with the new image and
   `canary_percent=10`, then the migrations job (`lims-<env>-migrate`), then `/ready` and the
   k6 smoke test against the tagged revision.
3. Production requires the approval of the `production` environment in GitHub.
4. After approval: migrations job → new revision at 10 % traffic → automated checks (k6 smoke,
   error rate < 1 % for 10 minutes) → `canary_percent=100`.
5. Watch the Grafana dashboard (p95 latency, error rate, failed tasks) for one hour.

Migrations are backward compatible with the previous revision (expand/contract): a column is
added before it is used, dropped one release after it stopped being read.
