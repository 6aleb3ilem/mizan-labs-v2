# ADR 0003 — Tenant context: `SET LOCAL` inside a request transaction, platform bypass

Date: 2026-09-11 · Status: accepted

## Context
SPEC §5, §27.1 and §27.6: row-level security enforces `tenant_id = current_setting('app.tenant_id')`,
set per request. `SET LOCAL` only lives inside a transaction, and a few operations (login by
e-mail, tenant provisioning, seeding, platform-operator screens) legitimately run before a
tenant is known.

## Decision
- Every API request and every background task runs inside `transaction.atomic()`; the tenant
  context manager executes `SET LOCAL app.tenant_id` right after entering it.
- Policies read `nullif(current_setting('app.tenant_id', true), '')::uuid` and are created
  with `FORCE ROW LEVEL SECURITY`, so the table owner is subject to them too (tests run as the
  application role, never as a superuser).
- A second setting, `app.rls_bypass = 'platform'`, is honoured by every policy. It is set only
  by `platform_scope()`, used by the login lookup, tenant provisioning, seeds and platform
  operator endpoints. Its use is audited.
- The immutable audit log is protected by a trigger that rejects UPDATE and DELETE in
  addition to the privilege revocation of SPEC Appendix B, so it holds under any role.

## Consequences
Cross-tenant reads are impossible even with a bug in a query predicate; the bypass surface is
one function that is easy to review.
