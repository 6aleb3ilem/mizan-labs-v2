# k6 budgets

- `smoke.js` — runs against every ephemeral revision in the pipeline (canary checks): health,
  JWKS, the authenticated read paths and one write, with the p95 thresholds of SPEC §1.4.
- `budgets.js` — the load scenario on seeded data (`manage.py seed_demo --scale large` once the
  Phase 1 modules exist); a threshold breach fails CI (SPEC §27.7, §30 rule 11).

```
k6 run -e BASE_URL=https://api.staging.example/api/v1 -e EMAIL=admin@demo.mizanlabs.dev -e PASSWORD=... -e TENANT=DEMO infra/k6/smoke.js
```
