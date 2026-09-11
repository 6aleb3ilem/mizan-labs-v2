# Mizan Labs Platform v2 — backend

Django 5 + Django Ninja modular monolith. One package `mizan/` with:

- `mizan/config` — settings (pydantic-settings), ASGI, URLs.
- `mizan/platform` — cross-cutting infrastructure: tenancy and RLS, ids, authz primitives,
  events/outbox, tasks, storage, formula engine, telemetry.
- `mizan/apps/*` — business apps (identity, org, config, crm, project, sales, lab, finance,
  assets, delivery, documents, notify, audit, analytics), each with `models.py`, `schemas.py`,
  `services.py`, `api.py`, `events.py`, `tasks.py`, `migrations/`, `tests/`.

See `../docs/SPEC.md` (single source of truth) and `../Makefile` for the developer workflow.
