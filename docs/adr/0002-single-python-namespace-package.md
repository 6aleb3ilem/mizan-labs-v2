# ADR 0002 — One Python namespace `mizan` for the backend

Date: 2026-09-11 · Status: accepted

## Context
SPEC §31 lays the backend out as `/backend/config`, `/backend/platform`, `/backend/apps/...`
as top-level Python packages. A top-level package named `platform` shadows the standard
library module `platform`, which `uuid`, `pydantic`, `psycopg` and Django import; the
application would fail before Django starts.

## Decision
The same layout lives one level down, inside a single package `mizan`:
`mizan/config` (settings, ASGI, URLs), `mizan/platform` (infrastructure), `mizan/apps/*`
(business apps). Django app labels stay the last path segment (`identity`, `org`, `config`…).

## Consequences
Imports are `from mizan.platform.db import ...`; the settings module is
`mizan.config.settings`. Nothing else in the specification changes.
