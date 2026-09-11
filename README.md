# Mizan Labs Platform v2

Multi-tenant laboratory operations platform for construction-materials testing laboratories:
client → project → quote → acceptance → intake → scheduled tests → measurements → validated
report → invoice → payment. Paperless, configurable, every issued document verifiable.

**The specification in `docs/SPEC.md` is the single source of truth.** Architecture decisions
that refine it are recorded in `docs/adr/`.

## Layout

| Path | Content |
|---|---|
| `backend/` | Python 3.12, Django 5 + Django Ninja, WeasyPrint + pyHanko document pipeline, Procrastinate jobs |
| `frontend/apps/` | back-office, admin console, client portal, verification site (React 19 + Vite) |
| `frontend/packages/` | design tokens, UI components, i18n, generated API client |
| `infra/` | Terraform (Cloud Run, Cloud SQL, KMS, Cloudflare), k6 budgets, runbooks |
| `docs/` | specification, ADRs, personas and journeys |

## Quick start

```bash
make setup            # uv sync + pnpm install
make db-up            # PostgreSQL 16, MinIO, Mailpit (Docker)
cp backend/.env.example backend/.env
make migrate seed     # schema + demo tenant (users listed by the seed command)
make dev              # API on :8000, worker, front-ends on :5173–:5176
make test lint        # everything CI runs
```

Without Docker, point `DATABASE_URL` at any PostgreSQL 16 with the `unaccent`, `pg_trgm` and
`citext` extensions available; the application role needs `CREATEDB` to run the test suite.
