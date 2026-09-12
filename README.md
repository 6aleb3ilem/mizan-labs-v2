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
make openapi          # export the OpenAPI document and regenerate the TypeScript client
make e2e              # Playwright end-to-end smoke (needs the built apps)
```

The seed creates the tenant `DEMO` with the branch `NKC`, the demo users below (password
`Demo-Passw0rd!`, change it with `--password`) and a platform operator
`operator@mizan-platform.dev`.

| User | Role |
|---|---|
| admin@demo.mizanlabs.dev | Tenant administrator (all branches) |
| aicha@demo.mizanlabs.dev | Commercial |
| moussa@demo.mizanlabs.dev | Laboratory reception |
| sidi@demo.mizanlabs.dev | Technician (concrete) |
| fatimetou@demo.mizanlabs.dev | Laboratory supervisor (concrete) |
| mohamed@demo.mizanlabs.dev | Finance |
| director@demo.mizanlabs.dev | Branch manager |

## Applications

| App | Dev port | Purpose |
|---|---|---|
| `frontend/apps/back-office` | 5173 | staff: home, projects, commercial, laboratory, finance, assets, delivery spaces |
| `frontend/apps/admin` | 5174 | administration console: organisation, access, numbering, vocabularies, workflows, catalog, documents, notifications, setup wizard |
| `frontend/apps/portal` | 5175 | client portal |
| `frontend/apps/verify` | 5176 | public verification site (installable PWA, offline QR check) |

`pnpm --filter @mizan/ui storybook` opens the design system with the accessibility addon.
The API is served on `:8000` (`/api/v1`, OpenAPI at `/api/v1/openapi.json`, docs at `/api/v1/docs`).

## Deployment

`.github/workflows/ci.yml` runs lint, type checks, the backend suite (PostgreSQL, RLS and
authorisation tests), the front-end suites and builds the image. `deploy.yml` applies the
Terraform in `infra/terraform` with the new image at 10 % traffic, runs the migrations job,
the readiness check and the k6 smoke, then promotes to 100 % (rollback on failure). Runbooks
are in `infra/runbooks/`.

Without Docker, point `DATABASE_URL` at any PostgreSQL 16 with the `unaccent`, `pg_trgm` and
`citext` extensions available; the application role needs `CREATEDB` to run the test suite.
