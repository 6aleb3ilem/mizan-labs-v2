# MIZAN LABS PLATFORM v2 — SYSTEM SPECIFICATION

Version 2.2 · 11 September 2026 · Single source of truth for the ground-up rebuild.

Change log
- 2.2: platform moved to Python (Django + Django Ninja, WeasyPrint + pyHanko document
  pipeline, Procrastinate jobs); deployment moved from a VPS to serverless managed
  infrastructure (Cloud Run + managed PostgreSQL + Cloudflare); payment terms become
  admin-defined templates; signatory configuration (image, drawn, digital certificate,
  external e-signature) is admin-driven; register of every configurable parameter
  (Appendix W); UX research, journeys and interaction specification added to §21.
- 2.1: consistency pass (order lines and invoice lines are tables, referenced views defined);
  added currency/FX and data-lifecycle rules, configuration change management, field work
  orders and in-situ tests, results analytics, cash-box day close, issuing external
  deliverables through the document pipeline, e-signature provider interface, printing
  architecture, default permission grid, UX writing rules, sizing model.
- 2.0: first complete English specification (supersedes all earlier drafts).
This document is complete on its own. A team, or an AI coding assistant, builds from it
without further explanation. Every decision below is final unless a newer numbered version
of this document changes it.

---

# PART I — FOUNDATIONS

## 1. Purpose and scope

### 1.1 Purpose
A multi-tenant laboratory operations platform that runs a construction-materials testing
laboratory end to end: client → project → quote → acceptance → sample intake → scheduled
tests → measurements → validated report → invoice → payment. No paper in the laboratory.
No business data hard-coded. Every issued document verifiable by anyone. Clients act on
their own data through a portal. Everything configured by administrators.

### 1.2 In scope
- Tenancy: tenants (companies) → branches (laboratories in cities/countries) → departments.
- Identity and access: users, memberships, roles, a permission matrix down to field level.
- Configuration: numbering schemes, vocabularies, workflows, catalog, test definitions,
  price lists, taxes, document templates, notification rules, branding.
- CRM: accounts, contacts, projects, participants, activities.
- Sales: project work breakdown, quotes with revisions, acceptance (portal, paper,
  e-signature), contracts, orders, amendments.
- Laboratory: intake, labels, specimens and samples, scheduling, stages and locations,
  worksheets (tablet, offline), computed results, review, report issuance and versions.
- Finance: invoices (milestones, progress), credit notes, treasury, payments, allocations,
  statements, dunning, payment-provider adapters.
- Assets: equipment, stock per location, consumables, rentals, sales, outings, transfers,
  maintenance, fleet documents.
- Delivery: phase templates and work orders for studies and field services.
- Documents: one rendering pipeline, sealing, signed QR, public verification, transparency log.
- Notifications: e-mail, SMS, WhatsApp, in-app, driven by rules.
- Audit, dashboards, exports.
- Three applications (back-office, admin console, client portal) and a public verification site.

### 1.3 Out of scope
- Migration of V1 data (V1 stays readable as history).
- General-ledger accounting (the platform exports to accounting software).
- HR and payroll.
- ISO/IEC 17025 accreditation features beyond what paperless operation requires.

### 1.4 Success criteria
| # | Criterion | How it is verified |
|---|---|---|
| 1 | Zero hard-coded business data | Lint rule on domain packages; admin can add a test, a status, a numbering scheme without a release |
| 2 | Enter once, appear everywhere | A quote line is traceable to its specimens, report and invoice line by foreign keys |
| 3 | Paperless laboratory | A PV is produced with no manual transcription from intake to issuance |
| 4 | Trustworthy documents | Any issued PDF verifies offline (QR) and online (registry); an altered copy fails |
| 5 | Right data to right people | A technician sees a project with no amounts; enforced in API responses, not UI |
| 6 | Fast | p95 API latency < 150 ms for reads, < 400 ms for writes; project page < 1 s; list pages virtualised |
| 7 | Cheap and scalable | Runs on serverless managed containers that scale from one instance to many with no code change; monthly cost tracks usage |
| 8 | Safe to change | Blue/green deploys, zero downtime, verified backups, full audit trail |

## 2. The business in one page

Mizan Labs is a construction-materials testing and engineering laboratory in Nouakchott,
Mauritania, a legal entity that issues and signs its own test reports. Other branches may
open in other cities or countries. The platform is also designed to host other laboratories
as separate tenants.

**Clients**: contractors, project owners (MO), engineering firms (MOE), technical control
bureaus (BCT), public agencies. An account has several contacts. A client has several
projects (chantiers) at once; a project sends samples for months.

**What is sold** (a *service* in the catalog, each with a *kind*):

| Kind | Examples | What acceptance provisions |
|---|---|---|
| LAB_TEST | concrete crushing, block crushing, sieve analysis, water content, Los Angeles, Micro-Deval, Atterberg, Proctor, CBR, steel tensile, bitumen, cement | expected intake quantities, scheduled test runs, worksheets, reports |
| FIELD_SERVICE | site sampling, in-situ tests, travel | a field work order |
| STUDY | geotechnical study, concrete mix design, asphalt mix design | a phased work order with responsibles and progress |
| RENTAL | moulds, presses, site equipment | stock reservation, rental note, return, late penalties |
| SALE | moulds, consumables | stock movement, sale note |
| FEE | file fee, urgency | a billable line |

**Two families of laboratory tests**
- *Specimen-based*: the client brings *n* identical specimens (cylinders 16×32, 15×30, cubes
  15×15, hollow/solid blocks…). Tests happen at fixed **ages** from the fabrication date
  (typically 7 and 28 days). Specimens are distributed across ages at intake; the schedule
  follows.
- *Sample-based*: one sample (soil, aggregate, bitumen, steel, cement) undergoes several
  different tests, each with its own inputs and formulas, sometimes after curing or soaking.

**Documents produced**: quote, contract, concrete crushing report (PV), block crushing
report, sieve-analysis report, water-content report, generic test report, invoice, credit
note, payment receipt, statement of account, rental note, sale note, outing note, transfer
note, labels, daily supervision digest.

**Fraud**: third parties forge reports and attribute them to the lab. Every document must
be verifiable in seconds, online and offline, and any alteration detectable.

**Paperless**: intake on a tablet, QR label per specimen, worksheet at the press, automatic
report, client notified by SMS/e-mail/WhatsApp, report in the portal. Printing remains
possible, with or without signature, chosen at print time.

## 3. Lessons from V1

### 3.1 Keep (ideas, not code)
| Idea | Why it matters |
|---|---|
| Project → tasks → line items; the quote adopts project tasks | The project is the centre; V1 already leaned this way |
| Payment milestones defined on the quote with labels and percentages | Correct place to define how invoicing will happen |
| Frozen line snapshot on invoices | An invoice must not change when the quote changes |
| Age-driven scheduling with "sum of quantities per age = total specimens" | The heart of a concrete lab |
| Single-outlier rule on specimens (drop one specimen ≥ 5 MPa below the rounded mean, recompute) | Encodes lab practice; becomes a configurable rule |
| Mix design, slump, placement, sampled-by captured at intake and printed on the PV | Required report content |
| Sample status history with physical locations (curing tanks) | Paperless tracking needs it |
| Phase templates with weighted responsibles (project-management module) | Good workflow primitive for studies |
| "PM" (pour mémoire) non-billable lines | Real commercial practice |
| Daily supervisor digest | Real operational need |

### 3.2 Never again
| V1 defect | V2 rule |
|---|---|
| Number formats, test list, VAT, bank account, director name, recipient e-mails in code | All configuration (Part III §10) |
| Statuses compared by label ("Confirmé") | States carry system semantics; code never reads labels |
| Three copies of the lab (concrete, blocks, samples) | One test-definition engine; tests are data |
| Intake is a blank form retyping client/project/quote | Intake is done against expected work from the order |
| One status field mixing negotiation, execution and money | Three derived states per work item |
| No quote revisions; sent quotes overwritten | Immutable revisions |
| Integer money, string dates, truncated percentages | Decimal money, typed dates, rounding rules |
| Client/project names copied onto lab records | Foreign keys only; names rendered at read time |
| One role string per user; API unauthenticated in production | Membership × role × scope × field groups; enforced in API and database |
| Four PDF generators | One document pipeline |
| No audit trail, no backups, secrets in repo | Append-only audit, verified backups, secret store |

## 4. Product principles (binding)

1. **Three tiers.** Everything is one of: *system semantics* (in code: `ACCEPTED`,
   `LAB_TEST`, `ISSUED`), *configuration* (admin console: statuses, categories, numbering,
   tests, prices, templates, roles), *data* (users' records). Only tier 1 lives in code, and
   tier 1 never contains a human label, number format, price, recipient or formula.
2. **Identity is never a label.** Every configurable thing has an id and an immutable code;
   labels are translations attached to it. References and rules use ids/codes only.
3. **State machines with semantics.** Every lifecycle record has admin-defined states; each
   state maps to exactly one system semantic; transitions require a permission and emit events.
4. **Derived, never typed.** Any state computable from other records is computed and read-only.
5. **Immutable when signed or invoiced.** Revisions and versions instead of edits.
6. **Events, not side-effects.** Provisioning, notifications and dashboards subscribe to events.
7. **Tenant and branch are first-class scopes** on every row, enforced by the database.
8. **One document pipeline.**
9. **Permission decides visibility and action** in the API and the query layer; the UI reflects.
10. **Performance is a feature.** Budgets in §1.4 are tested in CI.
11. **Boring, replaceable technology.** A modular monolith that scales horizontally; no
    microservices until a measured reason exists.

## 5. Tenancy model

```
Tenant (a company / laboratory group)       ← isolation boundary, branding, platform plan
 └─ Branch (a laboratory in a city/country)  ← legal identity, currency, tax, timezone, numbering, signatories, treasury
      └─ Department (Concrete, Soils & Aggregates, Geotechnics, Assets, Commercial, Finance…)
```

| Concern | Lives at |
|---|---|
| Data isolation, branding (logo, colours, document header), platform plan | Tenant |
| Legal name, registration numbers, address, logo override, signatories, bank accounts | Branch |
| Currency, VAT rules, rounding, timezone, working days, holidays, languages | Branch |
| Numbering schemes, document templates (overrides), price lists | Branch |
| Menu grouping, work routing, permission scoping, dashboards | Department |
| Users | Tenant-level identity; memberships per branch/department |

Rules:
- Every table has `tenant_id` and (where meaningful) `branch_id`. PostgreSQL row-level
  security enforces `tenant_id = current_setting('app.tenant_id')`; the API sets it per
  request. Branch scoping is enforced by the authorization layer's query predicates.
- Cross-branch operations (sample or equipment transfers) are explicit records.
- A tenant is created by the platform operator; a branch by the tenant admin (setup wizard).
- Theming: each tenant defines logo (SVG), primary colour, document header/footer texts.
  The default theme (§21) is used until changed.

## 6. Actors and applications

| Actor | Application | Intent |
|---|---|---|
| Commercial | Back-office / Commercial | Clients, projects, quotes, acceptance, follow-up |
| Lab reception | Back-office / Laboratory (tablet) | Intake against expected work, labels |
| Technician | Back-office / Laboratory (tablet) | Worksheets, measurements, stage changes |
| Lab supervisor | Back-office / Laboratory | Planning, review, issuance, variances |
| Finance | Back-office / Finance | Invoices, payments, treasury, statements |
| Assets staff | Back-office / Assets | Stock, rentals, outings, transfers, maintenance, fleet |
| Branch manager | Back-office / all | Approvals, signatures, dashboards |
| Tenant administrator | Admin console | Configure everything |
| Platform operator | Admin console (platform level) | Tenants, plans, keys, health |
| Client user | Client portal | Follow, accept, download, request, pay |
| Public verifier | Verification site | Authenticate a document |

Applications (separate builds, one API, one design system):
1. **Back-office** — `app.<domain>` — staff daily work, spaces composed from permissions.
2. **Admin console** — `admin.<domain>` — configuration; platform-operator section.
3. **Client portal** — `client.<domain>` — the client's own data.
4. **Verification site** — `verify.<domain>` — public, no login, works offline as a PWA.

All are responsive: desktop, tablet (mandatory for laboratory), phone (portal, consultation).

---

# PART II — THE END-TO-END BUSINESS FLOW

## 7. Flow, step by step

Each step names: screen, records created, state changes, events emitted.

### 7.0 Overview
```
ACCOUNT ─▶ PROJECT ─▶ WORK BREAKDOWN (tasks → work items)
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
      QUOTE (revisions)             variance items (unquoted work)
             │ Acceptance (portal OTP / paper scan / e-signature)
             ▼
          ORDER ──▶ provisioning: expected intakes · work orders · stock reservations · milestone instances
             ▼
INTAKE ─▶ LABELS ─▶ TEST RUNS (scheduled) ─▶ WORKSHEET ─▶ REVIEW ─▶ REPORT issued (sealed, QR)
                                                                         │
                                          notifications (SMS / e-mail / WhatsApp / portal) ◀┘
                                                                         │
                          milestone "on report" becomes invoiceable ◀────┘
                                                                         ▼
                       INVOICE ─▶ PAYMENT (cash / transfer / cheque / provider) ─▶ PAID
```

### 7.1 Account and contacts
- Screen: Commercial › Accounts › New.
- Records: `Account`, `Contact[]`. Portal login created by staff (temporary password,
  forced change). No self-signup.
- Rules: duplicate detection on normalised name and tax id; merge proposal.
- Events: `account.created`, `contact.created`, `portal_user.invited`.

### 7.2 Project
- Screen: Commercial › Projects › New (or from account).
- Records: `Project` with sites and participants (other accounts with a role: MO, MOE, BCT,
  contractor). Number from scheme PROJECT.
- Events: `project.created`.

### 7.3 Work breakdown
- Screen: Project › Work breakdown.
- Records: `Task` (heading), `WorkItem` (service + quantity + options). Items added by
  commercial staff when quoting or by lab staff as **variances** when unquoted work arrives.
- Derived states per item: commercial, execution, financial (§12.3).
- Events: `work_item.created`, `work_item.flagged_variance`.

### 7.4 Quote
- Screen: Project › Quotes › New (pre-filled with unquoted items) or Commercial › Quotes.
- Records: `Quote`, `QuoteRevision`, `QuoteLine[]`, `Milestone[]`.
- Rules: revision immutable once SENT; editing a sent revision creates the next; one item
  in one active ACCEPTED revision; discount fixed XOR percent; PM lines non-billable;
  totals computed server-side once; last milestone absorbs rounding; discount above
  threshold requires approval.
- Events: `quote.created`, `quote.revision_created`, `quote.sent`, `quote.approval_requested`,
  `quote.approved`, `quote.negotiating`, `quote.suspended`, `quote.refused`, `quote.expired`.

### 7.5 Acceptance, contract, order
- Acceptance is an evidence record bound to a revision hash: PORTAL (OTP by SMS/e-mail),
  PAPER (scan uploaded by staff), ESIGN (provider certificate).
- `Order` = frozen copy of accepted lines. Amendments supersede order lines explicitly.
- Contract optional, generated from a template over the accepted revision, own signature flow.
- Events: `quote.accepted`, `order.created`, `contract.generated`, `contract.signed`.

### 7.6 Provisioning (automatic, on `order.created`)
| Line kind | Creates |
|---|---|
| LAB_TEST | `ExpectedIntake` per item (quantity, specimen type, ages) |
| FIELD_SERVICE | `WorkOrder` (field) |
| STUDY | `WorkOrder` with phases from the template |
| RENTAL / SALE | `StockReservation` |
| all | `MilestoneInstance[]` from the payment schedule |
Events: `expected_intake.created`, `work_order.created`, `stock.reserved`, `milestone.instantiated`.

### 7.7 Intake
- Screen: Laboratory › Intake (tablet). Choose project → outstanding expected quantities →
  register specimens (type × qty) and/or samples (name, nature, materials) linked to items →
  test-specific intake fields (mix design, slump, sampled by…) → age distribution with
  Σ = total enforced on create and update → delivered by, received by, photos → labels.
- Unmatched arrivals create variance items; intake is never blocked.
- Events: `intake.registered`, `specimen.labelled`, `sample.registered`, `work_item.flagged_variance`.

### 7.8 Scheduling
- On `intake.registered`, `TestRun[]` are created per definition rule (ages → due dates;
  turnaround → business days; manual). Calendar per department; assignment; capacity.
- Events: `test_run.scheduled`, `test_run.assigned`, `test_run.due_tomorrow`, `test_run.overdue`.

### 7.9 Stages and locations
- Specimens/samples move through the definition's stages (received → curing @ location →
  testing → reported); each change is an event, triggered by scanning the label.
- Events: `stage.changed`.

### 7.10 Worksheet
- Screen: tablet; scan label → run opens with the definition's inputs; live validation;
  computed values displayed; rules applied; operator, instrument, time, photos recorded;
  offline capable.
- Overrides of computed values: separate permission, reason, old/new value, footnote on report.
- Events: `measurement.recorded`, `test_run.measured`, `computed_value.overridden`.

### 7.11 Review and report
- Screen: Laboratory › To review. Supervisor opens draft report; approve → issuance record,
  sealed PDF, QR; item delivered quantity increases.
- Versions supersede with reason; revocation with reason; nothing deleted.
- Events: `report.issued`, `report.superseded`, `report.revoked`, `work_item.delivered`.

### 7.12 Invoicing, payments, treasury
- Finance › To invoice lists triggered milestones and delivered-not-invoiced items.
- Invoice by milestones or by progress; gap-free number at issue; frozen lines; sealed PDF.
- Payment recorded manually (cash, transfer, cheque) or via provider adapter; allocations to
  invoices; one treasury entry per payment; statuses derived.
- Events: `invoice.issued`, `invoice.sent`, `credit_note.issued`, `payment.recorded`,
  `payment.allocated`, `invoice.paid`, `invoice.overdue`.

### 7.13 Client portal
- Client sees projects, work breakdown (execution and financial states), quotes (accept
  online), intakes and scheduled tests, reports (download, verify), invoices and statements,
  payments, requests, history, account settings.

### 7.14 Assets
- Rentals and sales come from orders; rental note at hand-over; return with condition;
  late penalties computed by rule → penalty line to invoice. Outings, transfers (stock per
  location), consumables ledger, maintenance, fleet documents.
- Events: `rental.started`, `rental.returned`, `rental.late`, `stock.moved`, `transfer.received`,
  `maintenance.due`.

### 7.15 Delivery (phased services)
- STUDY items instantiate a phase template into a work order; assignments; progress =
  weighted completed phases; lateness computed.
- Events: `phase.completed`, `work_order.late`, `work_order.completed`.

### 7.16 Closure
- Project closes when all items are delivered and paid (or cancelled). Full timeline remains.
- Events: `project.closed`.

---

# PART III — DOMAIN MODEL AND RULES

## 8. Conventions

| Topic | Rule |
|---|---|
| Identifiers | UUID v7 primary keys (time-ordered, index-friendly). Human numbers come from numbering schemes and are separate columns. |
| Common columns | `tenant_id`, `branch_id` (nullable only on tenant-level tables), `created_at`, `created_by`, `updated_at`, `updated_by`, `deleted_at`, `deleted_reason`, `row_version` (optimistic lock). |
| Money | `NUMERIC(18,2)` amount + `currency` (ISO 4217). Computed once, server-side. Branch rounding rule: HALF_UP to 2 decimals unless configured. Never floats. |
| Time | Instants `TIMESTAMPTZ` (UTC). Business dates `DATE` in branch timezone. Ages and due dates are dates. |
| Text and labels | Configurable entities have `code` (immutable, `^[A-Z0-9_.-]{2,64}$`) and rows in `i18n_text(entity, entity_id, field, locale, text)`. Unique on `(entity, field, locale, lower(text))` within tenant. |
| Soft delete | Anything a client has seen is soft-deleted with a reason; drafts may be hard-deleted. |
| Attachments | `attachment(owner_type, owner_id, kind, object_key, sha256, size, mime, uploaded_by, uploaded_at)`; stored in object storage; virus-scanned; images get thumbnails. |
| Search | PostgreSQL full-text + trigram indexes on numbers, names, labels in all locales. |
| Concurrency | `row_version` check on every update; counters and stock use atomic `UPDATE … WHERE` statements. |
| Pagination | Cursor-based (`?after=<opaque>&limit=50`), default 50, max 200; lists expose sort keys explicitly. |
| Errors | `{ code, message_key, params, details[] }` with HTTP status; `message_key` is translated client-side. |
| Idempotency | All POST creating records accept `Idempotency-Key`; stored 24 h per tenant. |
| Currency and FX | Every monetary record carries the currency of its branch. Quotes, orders, invoices and payments never mix currencies. Tenant-level dashboards convert with a tenant-managed rate table (`fx_rate(from, to, valid_from, rate)`) for reporting only; no business amount is ever converted. |
| Data lifecycle | Issued documents, audit events, invoices, payments: retained indefinitely. Drafts older than 12 months: purged by a job (audited). Attachments follow their owner. An account may request a full export of its data (portal, client admin) delivered as a ZIP with PDFs and CSVs; deletion requests are handled by anonymising contacts while keeping issued documents (legal). |
| Collaborative editing | Editable records show who else has the record open (presence via SSE); saves use `row_version`; a conflict returns both versions for the user to merge. Quote revisions in DRAFT may be soft-locked by their editor for 15 minutes (visible lock, overridable by a manager). |

## 9. Identity, roles and the permission matrix

### 9.1 Entities
| Entity | Fields |
|---|---|
| `user` | id, tenant_id, idp_subject, email, display_name, locale, mfa_enrolled, status (ACTIVE/DISABLED), last_login_at |
| `membership` | id, user_id, branch_id (nullable = all branches), department_id (nullable), role_id, account_id (client users), project_ids[] (client restriction), status |
| `role` | id, tenant_id, code, is_template, description |
| `grant` | id, role_id, resource, action, scope, field_groups[] |
| `api_key` | id, tenant_id, name, hashed_key, role_id, expires_at (integrations) |

### 9.2 Permission catalogue
**Resources**: `tenant`, `branch`, `department`, `user`, `role`, `numbering_scheme`,
`vocabulary`, `workflow`, `service_category`, `service`, `test_definition`, `specimen_type`,
`sieve_set`, `price_list`, `tax_rule`, `document_template`, `notification_rule`, `integration`,
`account`, `contact`, `project`, `task`, `work_item`, `quote`, `quote_revision`, `acceptance`,
`contract`, `order`, `expected_intake`, `intake`, `specimen`, `sample`, `test_run`,
`measurement`, `report`, `invoice`, `credit_note`, `payment`, `treasury_account`,
`treasury_entry`, `equipment`, `stock`, `consumable`, `rental`, `sale`, `outing`, `transfer`,
`maintenance`, `vehicle`, `fleet_document`, `phase_template`, `work_order`, `attachment`,
`comment`, `audit_event`, `dashboard`, `export`.

**Actions** (fixed): `view`, `create`, `edit`, `delete`, `submit`, `approve`, `issue`,
`sign`, `cancel`, `export`, `print`, `configure`, `assign`, `reassign`, `change_stage`,
`review_results`, `override_computed_value`, `allocate_payment`, `unlock_revision`,
`impersonate_view`.

**Scopes**: `ALL_BRANCHES`, `OWN_BRANCH`, `OWN_DEPARTMENT`, `ASSIGNED_TO_ME`, `OWN_RECORDS`,
`OWN_ACCOUNT` (client users).

**Field groups** (qualify `view`/`edit`):
- on `project`, `work_item`, `task`: `commercial` (unit prices, totals, discounts, margins),
  `financial` (invoices, payments, balances), `client_contact` (phones, e-mails);
- on `report`, `test_run`: `raw_measurements`;
- on `user`: `security`;
- on `account`: `financial`.

A `grant` = (resource, action, scope, field_groups). A role is a set of grants. A user's
effective permissions = union of grants of all their memberships, each grant bound to that
membership's branch/department/account.

### 9.3 Default role templates (editable, deletable)
| Role | Grants (summary) |
|---|---|
| Commercial | account/contact/project/task/work_item: view,create,edit (OWN_BRANCH, all field groups); quote/quote_revision: view,create,edit,submit,print,export; acceptance: create (PAPER); contract: view,create; order: view; invoice: view |
| Commercial manager | Commercial + quote: approve, sign; contract: sign; discount threshold override |
| Lab reception | project/work_item: view (OWN_BRANCH, no commercial/financial); intake: view,create,edit,print; specimen/sample: view,create,change_stage; expected_intake: view |
| Technician | test_run: view,edit (ASSIGNED_TO_ME); measurement: create,edit (ASSIGNED_TO_ME); specimen/sample: change_stage; attachment: create |
| Lab supervisor | all laboratory resources: view,create,edit,assign,reassign,review_results,override_computed_value (OWN_DEPARTMENT); report: issue,print,export; test_run: cancel |
| Finance | project: view (financial only); invoice/credit_note: view,create,issue,print,export,cancel; payment: view,create,allocate_payment; treasury_account/treasury_entry: view,create; account: view (financial) |
| Assets | equipment/stock/consumable/rental/sale/outing/transfer/maintenance/vehicle/fleet_document: all actions (OWN_BRANCH) |
| Branch manager | view on everything (OWN_BRANCH), approve/sign/issue on quote, contract, report, invoice; dashboard: view |
| Tenant administrator | configure on all configuration resources (ALL_BRANCHES); user/role: all; impersonate_view; no business data by default |
| Client user | project/work_item (execution+financial states, no commercial detail unless enabled)/quote/report/invoice/payment: view (OWN_ACCOUNT); acceptance: create (PORTAL); request: create |
| Client admin | Client user + contact/user (OWN_ACCOUNT): create, edit |

### 9.4 Enforcement
- Each API operation declares `(resource, action)`. Middleware resolves the caller's
  effective grants (cached per user, invalidated on grant/membership change), checks the
  action, and produces a **scope predicate** injected into the repository query
  (`branch_id IN (...)`, `assigned_to = me`, `account_id = ...`).
- Field groups are applied at response serialisation (fields **omitted**, never blanked)
  and at request binding (non-granted fields ignored with an audit note).
- Workflow transitions declare the required action; segregation-of-duties guards
  (`actor ≠ entrant`) are transition guards.
- Clients call `GET /me/permissions` once per session; UI composes menus, tabs, buttons,
  columns from it. UI never decides on its own.
- Admin console **"View as"**: pick a user → effective grants + read-only preview of their
  project page.
- Grant and membership changes are audited. Roles in use cannot be deleted; they are retired.
- Tenant admins cannot grant scopes beyond their tenant. Platform operators hold a separate
  platform role outside tenant RLS.

### 9.5 Portal feature toggles (per account, granted as scoped grants)
`quotes_visible`, `quotes_acceptable_online`, `reports_downloadable`, `invoices_visible`,
`online_payment`, `request_quote`, `request_invoice`, `restrict_contacts_to_projects`.

## 10. Configuration subsystems

### 10.1 Numbering schemes
| Field | Rule |
|---|---|
| `applies_to` | semantic document kind: ACCOUNT, PROJECT, QUOTE, ORDER, CONTRACT, INTAKE, SAMPLE, SPECIMEN, TEST_RUN, REPORT, INVOICE, CREDIT_NOTE, PAYMENT, RENTAL, SALE, OUTING, TRANSFER, WORK_ORDER, EQUIPMENT, MAINTENANCE |
| `scope` | branch (+ optional department) |
| `pattern` | tokens `{PREFIX}` literal, `{BRANCH}`, `{DEPT}`, `{YYYY}`, `{YY}`, `{MM}`, `{SEQ:n}`, free literals; e.g. `DV-{BRANCH}-{YYYY}-{SEQ:4}`, `{PREFIX}{SEQ:4}-{YY}` |
| `reset` | NEVER, YEARLY, MONTHLY |
| `gap_policy` | GAP_FREE (invoices, credit notes) or TOLERANT |
| `allocation` | ON_CREATE or ON_ISSUE (GAP_FREE must be ON_ISSUE; drafts display `DRAFT-<uuid short>`) |
| `effective_from`, `status` | DRAFT, ACTIVE, RETIRED; a version is immutable once it has allocated |
| preview | computed: "next number will be DV-NKC-2026-0187" |

Algorithm: `counter(scheme_version_id, period_key)` row; allocation = single statement
`UPDATE counter SET value = value + 1 WHERE … RETURNING value` inside the issuing
transaction; formatted with the pattern; stored on the record with `scheme_version_id`.
Reserved numbers (continuing a V1 series) are inserted as used with `reserved_by`.

### 10.2 Vocabularies
Simple lists: id, code, labels (i18n), colour, icon, order, active, extra JSON attributes.
Kinds: task_category, quote_condition, contact_function, participant_role (MO, MOE, BCT,
CONTRACTOR…), priority, sample_nature, material_family, block_type, specimen_shape,
curing_location, payment_method, reason (cancel, revoke, credit), client_tier, unit,
equipment_condition, vehicle_document_type. "Used by" is shown before retirement; retired
entries remain valid on historical records.

### 10.3 Workflows
```
workflow            (id, tenant_id, branch_id nullable, kind, version, status)
workflow_state      (id, workflow_id, code, labels, colour, semantic, is_initial, is_terminal, sla_days)
workflow_transition (id, workflow_id, from_state_id, to_state_id, required_action, guards[], effects[], order)
```
Semantics per kind (fixed in code):

| Kind | Semantics |
|---|---|
| PROJECT | OPEN, ON_HOLD, CLOSED, CANCELLED |
| QUOTE | DRAFT, PENDING_APPROVAL, SENT, NEGOTIATING, ACCEPTED, REFUSED, SUSPENDED, EXPIRED, CANCELLED |
| CONTRACT | DRAFT, SENT_FOR_SIGNATURE, SIGNED, CANCELLED |
| ORDER | OPEN, AMENDED, COMPLETED, CANCELLED |
| INTAKE | REGISTERED, PARTIALLY_PROCESSED, PROCESSED, CANCELLED |
| TEST_RUN | SCHEDULED, IN_PROGRESS, MEASURED, UNDER_REVIEW, VALIDATED, REPORTED, CANCELLED |
| REPORT | DRAFT, ISSUED, SUPERSEDED, REVOKED |
| INVOICE | DRAFT, ISSUED, CANCELLED (paid status is derived) |
| PAYMENT | RECORDED, REVERSED |
| RENTAL | RESERVED, ACTIVE, RETURNED, LATE, CLOSED, CANCELLED |
| SALE | RESERVED, DELIVERED, CANCELLED |
| OUTING | OPEN, PARTIALLY_RETURNED, CLOSED |
| TRANSFER | DRAFT, VALIDATED, IN_TRANSIT, RECEIVED, CANCELLED |
| MAINTENANCE | PLANNED, IN_PROGRESS, DONE, CANCELLED |
| WORK_ORDER | PLANNED, IN_PROGRESS, LATE, COMPLETED, CANCELLED |
| PHASE | PENDING, IN_PROGRESS, COMPLETED |

Guard catalogue (code): `has_billable_lines`, `totals_computed`, `discount_within_threshold`,
`acceptance_evidence_attached`, `actor_is_not_entrant`, `all_runs_of_intake_reported`,
`all_measurements_present`, `no_rule_blocking`, `stock_available`, `no_open_children`,
`signatory_authorised`, `invoice_has_lines`, `payment_fully_allocated`.

Effect catalogue (code): `freeze_revision`, `create_next_revision_on_edit`, `create_order`,
`provision_work`, `notify(rule_code)`, `make_milestone_invoiceable(trigger)`,
`reserve_stock`, `release_stock`, `request_signature`, `issue_document`, `increment_delivered`,
`close_parent_if_complete`, `allocate_number`.

Rules: the admin adds states, renames, reorders, adds transitions; every state has exactly
one semantic; at least one state per required semantic; new versions apply to new records.
Code evaluates `state.semantic`, never `state.code` or labels.

### 10.4 Catalog
```
service_category (tree: id, parent_id, code, labels, department_id, order)
service          (id, category_id, code, labels, department_id, kind, unit_of_sale, default_price_ref, active,
                  test_definition_id | phase_template_id | equipment_class_id | stock_item_id)
```
`kind ∈ {LAB_TEST, FIELD_SERVICE, STUDY, RENTAL, SALE, FEE}`. The laboratory menu is generated
from categories and ACTIVE test definitions.

### 10.5 Test definitions
```
test_definition (id, code, labels, category_id, department_id, method_ref, version, status DRAFT|ACTIVE|RETIRED,
                 unit_under_test SPECIMEN|SAMPLE, scheduling JSON, stages JSON, intake_fields JSON,
                 inputs JSON, computed JSON, aggregates JSON, rules JSON, required_equipment_class_id,
                 report_template_id, report_columns JSON, unit_of_sale)
specimen_type   (id, code, labels, shape CYLINDER|CUBE|PRISM|BLOCK, dims JSON {d, side, L, W, H}, derived JSON)
sieve_set       (id, code, labels, sizes_mm[] ordered)
```
- `scheduling`: `{type: NONE}` | `{type: AGE, reference_field: "fabrication_date", allowed_ages: [2,3,7,14,28,56,90]}` |
  `{type: TURNAROUND, business_days: 5}`.
- `stages`: ordered `[{code, labels, location_vocab_kind?, is_terminal}]`.
- `intake_fields`: `[{key, labels, type: text|number|date|enum|structured, unit?, required, options?, schema?}]`.
- `inputs`: `[{key, labels, type: number|text|bool|enum, unit, level: PER_SPECIMEN|PER_PORTION|PER_SERIES|PER_RUN, required, min, max, step}]`.
- `computed`: `[{key, labels, unit, level, formula, precision}]`.
- `aggregates`: `[{key, labels, unit, formula, precision}]` (formulas over per-specimen values: `avg`, `min`, `max`, `count`, `sum`, `stddev`).
- `rules`: `[{code, labels, expression, effect: FLAG|EXCLUDE_AND_RECOMPUTE|BLOCK, params}]`.
- Versioning: any change to inputs/computed/aggregates/rules creates a new version; a version
  is immutable once a `test_run` references it.

**Formula language**: a sandboxed expression language (no loops, no assignment, no I/O).
Grammar: numbers, identifiers (`inputs.load`, `specimen.d`, `run.total_mass`,
`series[i].cum_retained`), arithmetic `+ - * / ^`, comparison, boolean `and or not`,
`if(cond, a, b)`, functions `round(x,n) floor ceil abs sqrt pi min max avg sum count stddev`,
unit conversion `to(x, "MPa")` via a declared conversion table. Evaluation time-limited,
memory-bounded. Every computed value stores the formula version used.

### 10.6 Price lists and taxes
`price_list(id, branch_id, code, labels, currency, valid_from, valid_to, client_tier_id nullable, account_id nullable, status)`;
`price(id, price_list_id, service_id, specimen_type_id nullable, unit_price, min_qty)`;
resolution order: account-specific → tier → branch default, most recent valid.
`tax_rule(id, branch_id, code, labels, rate, applies_to_kinds[], active)`; account
`tax_exempt` flag with reason. Rounding rule on branch.

### 10.7 Document templates
`document_template(id, tenant_id, branch_id nullable, kind, locale, version, status, html, css, variables JSON, sample_data JSON, approved_by, approved_at)`.
`print_profile(id, kind, defaults JSON: signature_image, digital_signature, qr, watermark, paper, copies)`.
Contract articles and quote conditions are templates/vocabularies.

### 10.8 Notification rules
`notification_rule(id, event_code, audience JSON {roles[], contact_roles[], user_ids[]}, channels[], template_id, throttle JSON, digest JSON {cron, query_id}, active)`;
`message_template(id, code, locale, channel, subject, body)`; `contact_channel_preference(contact_id, channel, enabled)`;
`notification_delivery(id, rule_id, event_id, recipient, channel, rendered, status, attempts, last_error)`.

### 10.9 Branch settings
Signatories (user + signature image + kinds), treasury accounts, logos, legal texts, default
locales, working days, holidays, label printer profiles, portal defaults, discount approval
threshold, late-rental penalty rule, invoice due days, dunning schedule.

### 10.10 Payment terms templates
Payment milestones are never typed from scratch and never hard-coded. The administrator
defines **payment terms templates** per branch:
```
payment_terms_template (id, branch_id, code, labels, is_default, active,
  milestones: [ { order, label (i18n), percent | amount, trigger, trigger_params, due_days_after_trigger } ])
```
Examples the admin might create: "100 % à la commande"; "30 % à l'acceptation, 70 % à la
remise du rapport"; "40 % / 30 % / 30 % par phase". The quote builder offers the templates
of the branch (default pre-selected); the commercial user may adjust percentages, labels and
triggers on the quote only if the permission `quote.edit_payment_terms` is granted; any
adjustment is visible as "custom terms" on the quote and in the audit. Trigger types are
system semantics (ON_ACCEPTANCE, ON_DELIVERY, ON_REPORT, ON_DATE, ON_PHASE, MANUAL); their
labels, the default due days and the dunning schedule are configuration.

### 10.11 Signatories and signature modes
A **signatory** is an admin-configured person authorised to sign given document kinds for a
branch. The administrator chooses, per signatory and per document kind, the **signature
mode**:

| Mode | What the admin configures | What happens at issuance |
|---|---|---|
| IMAGE | Uploads the signature image and optional stamp image (PNG/SVG), sets position per template, approves the asset (version-controlled) | The image is placed on the rendition when the print option "signature image" is on; the canonical original is still sealed by the branch seal |
| DRAWN | Nothing to upload; the signatory draws once on a device (signature pad) and the drawing is stored as the image asset | Same as IMAGE |
| DIGITAL_CERTIFICATE | A personal signing certificate is provisioned for the signatory in the KMS (or an existing one imported); requires step-up authentication (MFA) at signing | The signatory's PAdES signature (visible or invisible) is applied at issuance; the PDF shows "signed by <name>, <role>, <organisation>" |
| EXTERNAL_ESIGN | Selects an e-signature provider configured in Integrations | Issuance sends the document to the provider for the signatory; the signed PDF returns and is sealed by the pipeline |

The same mechanism serves the client side: a quote or contract can require the client's
signature in mode EXTERNAL_ESIGN, or accept PAPER (scan) / PORTAL (OTP) per §13.5. A
document kind may require **several** signatories in order (e.g. supervisor then director);
the workflow's `request_signature` effect drives the sequence. Nothing about who signs, how,
or where the image sits is in code.

### 10.12 Configuration change management
- Every configuration entity is versioned; activation is an explicit action with an
  effective date; the previous version stays attached to the records that used it.
- Changes to workflows, test definitions and templates go through DRAFT → (optional
  approval by a second administrator, per tenant setting) → ACTIVE; a **simulator/sandbox**
  exists for each.
- Configuration can be exported as a signed bundle (JSON) and imported into another
  environment (staging → production) or another branch/tenant; imports show a diff and are
  applied atomically.
- "Used by" counts are shown before retiring anything; retired entries remain resolvable
  for historical records and are hidden from pickers.
- All configuration changes are audit events with before/after; the admin console shows a
  configuration changelog per section with one-click rollback (creates a new version equal
  to the old one; never rewrites history).

## 11. CRM

| Entity | Fields |
|---|---|
| `account` | number, code, legal_name, trade_name, legal_form, tax_id, other_ids JSON, addresses[], phone, email, client_tier_id, tax_exempt, tax_exempt_reason, document_locale, portal_features[], notes, state (workflow ACCOUNT: ACTIVE, INACTIVE, BLOCKED) |
| `contact` | account_id, first_name, last_name, function_id, phone, whatsapp, email, roles[] (COMMERCIAL, TECHNICAL, ACCOUNTING, SIGNATORY), channel_preferences, locale, portal_user_id nullable, active |
| `project` | number, account_id, title, description, location, sites[] (name, address, geo), participants[] (account_id, role_id), owner_user_id, planned_start, planned_end, state (workflow PROJECT), attachments |
| `activity` | owner (account/project), type (CALL, MEETING, NOTE, REQUEST), author, at, text |
| `client_request` | account_id, contact_id, project_id nullable, type (QUOTE, INVOICE, QUESTION), text, attachments, state (OPEN, IN_PROGRESS, CLOSED), converted_to (project/quote id) |

Rules: account number from scheme ACCOUNT; duplicate check on `lower(unaccent(legal_name))`
and `tax_id`; merge keeps the older id and re-points foreign keys; contacts with role
SIGNATORY may accept quotes.

## 12. Project and work breakdown

### 12.1 Entities
| Entity | Fields |
|---|---|
| `task` | project_id, title, category_id, priority_id, due_date, owner_user_id, order |
| `work_item` | task_id, project_id, service_id, quantity, unit, specimen_type_id nullable, options JSON (ages[], dimensions…), notes, origin (QUOTE, VARIANCE), qty_expected, qty_received, qty_reported, qty_invoiced, delivered_at |

### 12.2 Quantities (maintained by events)
- `qty_expected` += accepted quantity on `order.created`; adjusted by amendments.
- `qty_received` += specimens/samples linked at `intake.registered`.
- `qty_reported` += units covered by `report.issued` (per definition's unit of sale).
- `qty_invoiced` += invoiced quantity on `invoice.issued` (progress invoices).

### 12.3 Derived states (read models, recomputed on relevant events)
**Commercial** (from quote revisions containing the item):
```
if item in an ACCEPTED revision                      → ACCEPTED
else if in a SENT/NEGOTIATING/PENDING_APPROVAL rev    → that semantic
else if in a DRAFT revision                           → DRAFT
else if in REFUSED/EXPIRED/CANCELLED only             → that semantic
else                                                  → NOT_QUOTED
(SUSPENDED quote → SUSPENDED)
```
**Execution**:
```
qty_received == 0 and no work order started            → NOT_STARTED (LAB_TEST: AWAITING_SAMPLES once accepted)
qty_received > 0 and qty_reported == 0                 → IN_PROGRESS
0 < qty_reported < qty_expected                        → PARTIALLY_DELIVERED
qty_reported >= qty_expected (and > 0)                 → DELIVERED
STUDY/FIELD: from work order state
RENTAL/SALE: from rental/sale state (ACTIVE → IN_PROGRESS, RETURNED/DELIVERED → DELIVERED)
```
**Financial**:
```
no milestone instance invoiceable and qty_invoiced == 0           → NOT_INVOICEABLE
some milestone instance INVOICEABLE or delivered-not-invoiced qty → INVOICEABLE
invoiced amount > 0 and paid == 0                                  → INVOICED
0 < paid < invoiced                                                → PARTIALLY_PAID
paid >= invoiced and invoiced covers item                          → PAID
```
Milestone-based orders attribute financial state to all items of the order pro rata.

### 12.4 The project page
One page for everyone; tabs and columns composed from permissions (§22.3). Header KPIs:
items count, commercial summary, execution (delivered/total), financial (invoiced/paid),
overdue runs. The page is a view of the graph from the project node.

## 13. Sales

### 13.1 Entities
| Entity | Fields |
|---|---|
| `quote` | number, project_id, account_id, currency, locale, conditions[] (vocab ids), validity_days, notes_client, notes_internal, owner_user_id, state (workflow QUOTE), current_revision_no |
| `quote_revision` | quote_id, revision_no, frozen, frozen_at, discount_type (NONE, FIXED, PERCENT), discount_value, tax_rule_id, subtotal, discount_amount, taxable, tax_amount, total, content_hash, pdf_document_id |
| `quote_line` | revision_id, work_item_id, order, description_override, quantity, unit_price, line_discount_percent, billable, line_total |
| `milestone` | revision_id, template_id (payment terms template used), is_custom, order, label, percent nullable, amount nullable, trigger (ON_ACCEPTANCE, ON_DELIVERY, ON_REPORT, ON_DATE, ON_PHASE, MANUAL), trigger_ref (item ids / date / phase), due_days_after_trigger |
| `acceptance` | revision_id, method (PORTAL, PAPER, ESIGN), contact_id, accepted_at, evidence JSON, revision_hash |
| `contract` | revision_id, template_id, number, representatives JSON, state (workflow CONTRACT), pdf_document_id |
| `order` | number, acceptance_id, project_id, account_id, currency, amends_order_id nullable, state (workflow ORDER) |
| `order_line` | order_id, work_item_id, service_id, description (frozen), quantity, unit_price, billable, line_total, status (OPEN, SUPERSEDED, CANCELLED), superseded_by_line_id |
| `milestone_instance` | order_id, milestone_id, amount, trigger, state (PENDING, INVOICEABLE, INVOICED), triggered_at, invoice_id |

### 13.2 Totals algorithm (server-side, on every revision save)
```
for each billable line: line_total = round(quantity × unit_price × (1 − line_discount_percent/100), 2)
subtotal        = Σ line_total
discount_amount = FIXED: min(discount_value, subtotal) ; PERCENT: round(subtotal × value/100, 2) ; NONE: 0
taxable         = subtotal − discount_amount
tax_amount      = account.tax_exempt ? 0 : round(taxable × tax_rule.rate/100, 2)
total           = taxable + tax_amount
milestones (percent): amount_i = round(total × p_i/100, 2) for i < n ; amount_n = total − Σ amount_i  (rounding absorbed)
milestones (amount): Σ must equal total, else validation error
```
PM lines (`billable=false`) print without amount and never enter totals.

### 13.3 Quote state machine (default template; admin may extend)
| From | To | Action | Guards | Effects |
|---|---|---|---|---|
| DRAFT | PENDING_APPROVAL | submit | has_billable_lines, totals_computed, NOT discount_within_threshold | notify(approvers) |
| DRAFT | SENT | submit | has_billable_lines, totals_computed, discount_within_threshold | freeze_revision, allocate_number(if first), issue_document(QUOTE), notify(client_quote_sent) |
| PENDING_APPROVAL | SENT | approve | signatory_authorised | freeze_revision, issue_document, notify |
| PENDING_APPROVAL | DRAFT | edit | — | — |
| SENT | NEGOTIATING | edit | — | — |
| SENT/NEGOTIATING | DRAFT (new revision) | edit | — | create_next_revision_on_edit |
| SENT/NEGOTIATING | ACCEPTED | approve (acceptance) | acceptance_evidence_attached | create_order, provision_work, make_milestone_invoiceable(ON_ACCEPTANCE), notify(internal_accepted) |
| SENT/NEGOTIATING | REFUSED | cancel | reason | notify(internal) |
| SENT/NEGOTIATING | SUSPENDED | edit | reason | — |
| SUSPENDED | NEGOTIATING | edit | — | — |
| SENT | EXPIRED | (system, validity elapsed) | — | notify(owner) |
| any non-terminal | CANCELLED | cancel | reason | release reservations if any |

### 13.4 Revisions
- Revision 1 is created with the quote. `frozen=true` on SENT.
- Any edit on a frozen revision copies it into revision n+1 (DRAFT); the quote's state returns
  to DRAFT while the frozen PDF of n remains downloadable.
- Comparison view between two revisions (lines added/removed/changed, totals).
- Acceptance binds `revision_hash` = SHA-256 of canonical JSON of the revision content.

### 13.5 Acceptance
| Method | Evidence stored |
|---|---|
| PORTAL | portal user id, contact id, OTP challenge id (6 digits, 10 min, 5 attempts, sent to registered phone/e-mail), IP, user agent, terms version shown |
| PAPER | scan attachment id, received_by user, received_at, optional stamp photo |
| ESIGN | provider, envelope id, signer identity, completion certificate attachment |
Rules: contact must carry role SIGNATORY (or account allows any contact, configurable);
one acceptance per revision; acceptance is immutable; a later amendment references it.

### 13.6 Orders and amendments
- `order.created` copies accepted lines. Provisioning per §7.6 runs in the same transaction
  as the acceptance (outbox events dispatch the notifications).
- Amendment = new quote revision covering changed/added items, marked `amends_order_id`;
  on acceptance, superseded lines are closed (remaining expected quantities cancelled) and
  new lines provisioned.
- "Use as template": copy lines of a revision into another project's work breakdown
  (creates work items), never copies acceptance or numbers.

### 13.7 Contract
Generated from the CONTRACT template with variables from the revision, account and branch;
representatives entered; states DRAFT → SENT_FOR_SIGNATURE → SIGNED (evidence like
acceptance: paper scan or e-sign certificate); sealed PDF; visible in portal.

## 14. Laboratory

### 14.1 Entities
| Entity | Fields |
|---|---|
| `expected_intake` | order_id, work_item_id, test_definition_id, specimen_type_id nullable, qty_expected, ages[] nullable, qty_received |
| `intake` | number, project_id, received_at, delivered_by, delivered_phone, received_by_user_id, intake_fields JSON (typed per definitions involved), photos[], state (workflow INTAKE) |
| `specimen` | intake_id, work_item_id, specimen_type_id, position, label_token, planned_age, current_stage_code, current_location_id, status (OK, MISSING, DAMAGED) |
| `sample` | intake_id, work_item_ids[], name, nature_id, materials JSON [{name, unit, qty}], label_token, current_stage_code, current_location_id |
| `test_run` | number, test_definition_id, definition_version, work_item_id, intake_id, specimen_ids[] / sample_id, due_date, age nullable, assigned_user_id, equipment_id, state (workflow TEST_RUN), measured_at, reviewed_by, reviewed_at |
| `measurement` | test_run_id, level, subject_id (specimen/portion/series index), key, value_num, value_text, unit, recorded_by, recorded_at, device_time, offline_batch_id |
| `computed_value` | test_run_id, level, subject_id, key, value, unit, formula_version, overridden, override_reason, original_value, overridden_by, overridden_at |
| `stage_event` | subject_type, subject_id, from_stage, to_stage, location_id, by_user, at |
| `report` | number, project_id, test_run_ids[], version, supersedes_report_id, state (workflow REPORT), issued_document_id, reason |

### 14.2 Intake rules
- The screen lists `expected_intake` rows of the project with `qty_expected − qty_received > 0`.
- Specimen registration: for each (specimen_type, qty) linked to an expected intake; positions
  1..n; `label_token` = random 128-bit id encoded base32.
- Age distribution: `[{age, qty}]`, `Σ qty = total specimens` on create and on update; each
  age must be in the definition's allowed ages; due date = reference date + age.
- Intake fields validated against the union of the involved definitions' `intake_fields`.
- Over-delivery: quantity beyond expected creates a variance `work_item` (origin VARIANCE)
  and a notification to the commercial owner. Under-delivery leaves the expected open.
- Labels printed (ZPL for label printers or PDF sheet); reprint allowed and logged.

### 14.3 Scheduling algorithm
```
on intake.registered:
  for each work item with scheduling AGE:
     for each (age, qty) in distribution: create test_run(due_date = reference + age, specimens = next qty positions)
  for each work item with scheduling TURNAROUND: create test_run(due_date = add_business_days(received_at, days))
  for NONE: create test_run(due_date = null) awaiting manual planning
daily job (branch timezone 06:00): mark runs due tomorrow (event), mark overdue runs (event)
```
Capacity view: runs per day per department vs configurable daily capacity; overbooked days flagged.

### 14.4 Worksheet and computation
- Worksheet is generated from the definition version: inputs grouped by level; per-specimen
  rows; live validation (`min`, `max`, `required`, monotonic series).
- On each save: compute `computed` per subject, then `aggregates`, then evaluate `rules`
  in order; `EXCLUDE_AND_RECOMPUTE` marks subjects excluded (flag + reason) and re-runs
  aggregates without them; `BLOCK` prevents `MEASURED` transition; `FLAG` annotates.
- Overrides: permission `override_computed_value`; stores original; report footnote.
- Missing/damaged specimen: status set with reason; excluded from aggregates; counted in
  the report.
- Offline: measurements queued locally with `offline_batch_id` and device time; server
  applies in order; conflicts (same subject/key by two devices) resolved last-write-wins
  with both values kept in audit.

### 14.5 Review and report issuance
- `MEASURED → UNDER_REVIEW` (review_results) → `VALIDATED` (guard actor_is_not_entrant
  configurable per branch) → `REPORTED` on `report.issued`.
- A report covers one or more validated runs of the same project and definition; draft
  rendered from `report_template_id`; issuance creates `issued_document` (§18), seals PDF,
  increments `qty_reported`, emits events.
- New version: copies the report, links `supersedes_report_id`, requires reason; old
  document status → SUPERSEDED. Revocation: reason, document status → REVOKED.

### 14.6 The four V1 tests as definitions
**CONCRETE_COMPRESSION**
```
unit_under_test: SPECIMEN ; specimen types: CYL_16x32 (d=16), CYL_15x30 (d=15), CUBE_15 (side=15)
scheduling: AGE from intake_fields.fabrication_date, allowed [2,3,7,14,28,56,90]
intake_fields: fabrication_date(date, req), sampling_by(enum LAB|CLIENT), structure_part(text), site(text),
               slump_cm(number), placement(text), mix_design(structured: gravel1, gravel2, sand1, sand2, cement, admixture, water → {name, dosage})
inputs (PER_SPECIMEN): weight_kg (0–50), load_kgf (0–200000)
computed (PER_SPECIMEN):
   section_cm2   = if(specimen.shape == "CYLINDER", pi * specimen.d^2 / 4, specimen.side^2)
   stress_kgcm2  = round(inputs.load_kgf / section_cm2, 0)
   stress_mpa    = round(stress_kgcm2 / 10, 1)
aggregates: mean_mpa = round(avg(stress_mpa), 1) ; n = count(stress_mpa)
rules: SINGLE_OUTLIER: expression "count(where(round(avg(stress_mpa),1) - stress_mpa >= params.threshold)) == 1"
       effect EXCLUDE_AND_RECOMPUTE (exclude the minimum), params {threshold: 5}
       MULTI_OUTLIER: "count(where(... >= params.threshold)) >= 2" effect FLAG
report: PV_CONCRETE ; columns [ref, age, weight_kg, load_kgf, stress_kgcm2, stress_mpa, mean_mpa]
```
**BLOCK_COMPRESSION**: SPECIMEN; types HOLLOW, SOLID, HOURDIS with L, W, H; inputs weight,
load, gross_area (default L×W, editable), net_area (default type factor × gross, editable);
computed gross_kgcm2, net_kgcm2, net_mpa = net_kgcm2/10; aggregate mean_net_mpa; same outlier
rules; report PV_BLOCKS.

**SIEVE_ANALYSIS**: SAMPLE; inputs PER_RUN total_mass_g, sieve_set; PER_SERIES cum_retained_g per
sieve; computed pct_retained = cum_retained/total_mass×100, pct_passing = 100 − pct_retained;
rules: cum_retained non-decreasing (BLOCK), cum_retained ≤ total_mass (BLOCK); report table + curve.

**WATER_CONTENT**: SAMPLE; PER_PORTION wet_plus_tare, dry_plus_tare, tare; computed water = wet −
dry, dry_net = dry − tare, w_pct = water/dry_net×100 (dry_net > 0 else BLOCK); aggregate mean_w.

### 14.7 Tests to define in the console (from V1's list; order by sales volume)
Soils: water content ✔, specific gravity, bulk density, Atterberg limits, sand equivalent,
Proctor normal/modified, CBR, oedometer, shear, permeability, hydrostatic weighing, absorption.
Aggregates: sieve analysis ✔, Los Angeles, Micro-Deval, methylene blue, surface cleanliness,
aggregates for asphalt. Concrete: compression ✔, mix design (STUDY), splitting tensile. Blocks:
compression ✔. Steel: tensile, bending. Bitumen/asphalt: mix design levels 0–2 (STUDY), binder
extraction, binder content by ignition, penetration, ring and ball, flash point, ductility,
viscosity, Duriez, gyratory compaction, rutting. Cement: Vicat setting time, compressive strength.
In-situ: defined by the lab. Adding a test never requires a release.

### 14.8 Field work orders and in-situ tests
- FIELD_SERVICE items create a `work_order(type=FIELD)` with a visit: planned date and time,
  site (project site), assigned technician, vehicle (from Assets), checklist (from the
  service's protocol), expected samples to bring back.
- In-situ tests (plate load, sand cone density, nuclear gauge, Schmidt hammer, pull-out…)
  are **test definitions** like any other, with `unit_under_test = SAMPLE` and inputs at
  `PER_RUN`/`PER_SERIES` levels; the worksheet runs on the phone or tablet at the site,
  offline, with GPS position, timestamps and photos captured automatically.
- Samples collected on site are pre-registered from the field (sample name, nature, GPS,
  photo) and become an intake when they reach the laboratory (scan → attach to the
  pre-registration), so chain of custody starts at the site.
- Visit completion emits `work_order.completed` (or phase completion) and can trigger
  ON_DELIVERY milestones.

### 14.9 Results analytics
- **Project strength history**: for every project with concrete runs, a chart of mean MPa
  by fabrication date and age (7 d, 28 d series), with target strength (from intake field
  `target_class`, optional) and the regulatory threshold lines; visible on the project Tests
  tab and in the portal.
- **Mix-design statistics**: per mix design signature (cement name and dosage, W/C), mean
  and standard deviation of 28-day strength across projects of the account (staff only).
- **Per-test dashboards** (generated from the definition): runs per period, turnaround,
  distribution of the main aggregate, rule hits (outliers), overrides count, technicians.
- **Supplier comparison** (aggregates/blocks): results grouped by the sample's `supplier`
  intake field when present.
All analytics read from read models; none of them alters results.

## 15. Finance

### 15.1 Entities
| Entity | Fields |
|---|---|
| `invoice` | number (gap-free), account_id, project_id, order_id nullable, source (MILESTONES, PROGRESS, MANUAL), subtotal, tax, total, currency, due_date, treasury_account_id (printed), state (workflow INVOICE), issued_document_id, paid_status derived (UNPAID, PARTIALLY_PAID, PAID, OVERDUE) |
| `invoice_line` | invoice_id, order, description (frozen), quantity, unit_price, tax_rate, line_total, work_item_id nullable, milestone_instance_id nullable, order_line_id nullable |
| `cash_day_close` | treasury_account_id (CASH), date, opening_balance, expected_closing, counted_closing, variance, counted_by, approved_by, notes, denominations JSON |
| `credit_note` | number, invoice_id, reason_id, lines[], total, issued_document_id |
| `payment` | number, account_id, amount, currency, method_id, paid_at, reference, proof attachment, recorded_by, treasury_account_id, provider_intent_id nullable, state (RECORDED, REVERSED) |
| `payment_allocation` | payment_id, invoice_id, amount |
| `treasury_account` | branch_id, type (BANK, CASH), label, iban, currency, printed_on_invoices |
| `treasury_entry` | treasury_account_id, direction (IN, OUT, TRANSFER_IN, TRANSFER_OUT), amount, at, origin (payment, refund, expense, transfer), label, counter_entry_id |
| `payment_intent` | provider, invoice_id, amount, provider_ref, status (CREATED, PENDING, SUCCEEDED, FAILED, EXPIRED), events JSON |
| `dunning_run` | invoice_id, level, sent_at, channel |

### 15.2 Invoicing algorithms
- **From milestones**: pick INVOICEABLE milestone instances of one order; line per milestone
  (`label`, amount); tax per order's tax rule; on issue: number allocated (GAP_FREE, ON_ISSUE),
  instances → INVOICED.
- **From progress**: pick delivered-not-invoiced quantities of items (qty_reported −
  qty_invoiced) at accepted unit prices; on issue: `qty_invoiced` updated.
- **Manual**: free lines (permission), still tied to account and optionally project.
- Issue → `issued_document`, sealed PDF, `invoice.issued`, portal, notification.
- Cancel only while DRAFT; after issue, credit note.

### 15.3 Payments and derived status
```
paid(invoice)   = Σ allocations − Σ credit notes applied
paid_status     = paid == 0 ? (due_date < today ? OVERDUE : UNPAID) : paid < total ? PARTIALLY_PAID : PAID
account balance = Σ issued invoices − Σ credit notes − Σ payments
```
Allocation UI proposes oldest-first; over-allocation impossible; unallocated remainder stays
on account as credit. Each payment creates exactly one `treasury_entry` (IN); reversal creates
an OUT with link.

### 15.4 Payment-provider adapter (placeholder now, providers later)
```
interface PaymentProvider
  createIntent(invoice, amount, payerContact) → {providerRef, instructions(redirectUrl|ussd|qr), expiresAt}
  handleWebhook(rawBody, signature) → PaymentEvent{providerRef, status, amount, paidAt}
  query(providerRef) → status
  capabilities() → {currencies[], min, max, refunds}
```
Implementations: `manual` (record with proof) shipped; `bankily`, `masrivi`, `sedad` added
when APIs arrive. Reconciliation job polls PENDING intents and matches statements; mismatches
go to a Finance queue. On SUCCEEDED: create `payment` + allocation automatically.

### 15.5 Statements and dunning
Statement per account/project/period (invoices, credit notes, payments, running balance) as
PDF and portal view. Dunning schedule per branch (e.g. D+7, D+21, D+45) via notification
rules; suspend per invoice with reason.

### 15.6 Cash box day close
Each CASH treasury account is closed daily: the system computes the expected closing
balance from entries; the cashier enters the counted amount (with denominations); a variance
creates an ADJUSTMENT entry requiring approval by Finance or the branch manager; the close
is an issued internal document (receipt of close) and cannot be reopened, only corrected by
a dated adjustment. Cash deposits to bank are TRANSFER entries with the bank slip attached.

## 16. Assets

| Entity | Fields |
|---|---|
| `equipment_class` | category, code, labels, rentable, sellable, daily_rate, monthly_rate, requires_calibration |
| `equipment` | class_id, code, serial, condition_id, state (ACTIVE, MAINTENANCE, OUT_OF_SERVICE), location_id, calibration_due |
| `stock_location` | branch_id, site, name |
| `stock_level` | item (class or consumable), location_id, qty_total, qty_reserved, qty_available (derived) |
| `stock_movement` | item, from_location, to_location, qty, reason (RENTAL_OUT, RENTAL_IN, SALE, OUTING_OUT, OUTING_IN, TRANSFER, ADJUSTMENT, PURCHASE), ref_type, ref_id, by, at |
| `rental` | order_id, lines[] (class_id, qty, unit, duration, rate, line_total), start_at, due_back_at, returned_at, state (workflow RENTAL), penalty_amount, condition_on_return |
| `sale` | order_id, lines[], delivered_at, state |
| `outing` | destination (site/department/person), lines[] with returned_qty, state |
| `transfer` | from_location, to_location, lines[] (item, qty, received_qty), state (workflow TRANSFER) |
| `consumable` | code, labels, unit, threshold; movements in `stock_movement` |
| `maintenance` | equipment_id, type (PREVENTIVE, CORRECTIVE), planned_at, done_at, cost, notes, state |
| `vehicle`, `fleet_document` | plate, model; document type (FUEL_SLIP, FINE, PURCHASE_ORDER, MAINTENANCE_ORDER), lines JSON, amount, date |

Rules:
- `qty_available = qty_total − qty_reserved`; reservation on `order.created`; release on cancel.
- Every quantity change is a `stock_movement`; levels are recomputed from movements (no
  free-hand edits); adjustments require reason.
- Rental total = Σ qty × rate(unit) × duration; late days = `today − due_back_at` (business
  days configurable); penalty = rule per branch (e.g. daily_rate × late_days × factor) → a
  penalty work item + milestone invoiceable.
- Transfers move quantities between locations; partial receipts keep the remainder IN_TRANSIT.
- Equipment in MAINTENANCE/OUT_OF_SERVICE cannot be rented or used as instrument on runs.

## 17. Delivery (phased services)

| Entity | Fields |
|---|---|
| `phase_template` | service_id, phases[] {code, labels, weight, responsible_category_id, optimal_days, max_days} |
| `work_order` | number, work_item_id, project_id, department_id, type (FIELD, STUDY), phases[] instantiated, planned_start, deadline_optimal, deadline_max, progress (derived), state (workflow WORK_ORDER) |
| `phase` | work_order_id, code, order, weight, state (PHASE), started_at, completed_at |
| `phase_assignment` | phase_id, responsible_id, is_principal, weight_percent |
| `responsible` | user_id nullable, name, category_id, active |

Progress = Σ weight(completed phases) / Σ weight. Late if `today > deadline_max` and not
completed (event `work_order.late`). Completing the last phase marks the item DELIVERED and
fires ON_DELIVERY milestones.

## 18. Documents and verification

### 18.1 Pipeline
```
template (HTML/CSS, per kind & locale, versioned) + data → render (headless Chromium) → PDF
→ PDF/A-3 conversion → sealing (PAdES-B-LTA, invisible seal with the branch key, RFC 3161 timestamp)
→ object storage (immutable key by sha256) → issued_document row → QR payload signed → events
```
Runs in workers; a request never renders inline. Rendering is deterministic: same template
version + same data → same content hash (timestamps excluded from hash input).

### 18.2 Entities
| Entity | Fields |
|---|---|
| `issued_document` | id, kind, number, branch_id, subject JSON {account, project, refs}, digest JSON (kind-specific), issued_at, issued_by, signatory_id, template_version, content_hash, pdf_object_key, pdf_sha256, status (CURRENT, SUPERSEDED, REVOKED), superseded_by_id, revoked_reason, verify_token (128-bit random, base32), short_code (6 chars, unambiguous alphabet), transparency_leaf_index |
| `rendition` | issued_document_id, options JSON, produced_by, produced_at, object_key, sha256 |
| `verification_attempt` | token, short_code_given, ip_hash, user_agent, at, outcome |
| `signing_key` | branch_id, kms_key_id, algorithm (Ed25519 for QR, RSA-3072/ECDSA-P256 for PAdES), public_jwk, valid_from, valid_to, status |
| `transparency_leaf` | index, issued_document_id, leaf_hash, tree_head_hash, published_at |

### 18.3 Approval, signature and rendition
Signature follows the signatory's configured mode (§10.11). IMAGE/DRAWN modes affect only
renditions; DIGITAL_CERTIFICATE and EXTERNAL_ESIGN modes are part of issuance and require
the signatory's step-up authentication or the provider's completion. In every mode the
canonical original carries the branch seal.
- **Approval** happens once in the workflow (permission `issue`/`sign`); it creates the
  `issued_document` and the sealed canonical original.
- **Rendition** is produced on demand with print options. Defaults per kind from the print
  profile, overridable per print (subject to permission `print`):

```
Print / Export
  [x] Signature image (signatory: <name>)       — the V1 behaviour, kept
  [ ] Digital signature (visible certificate)   — PAdES visible signature with signatory identity
  [x] QR + verification code
  [ ] Watermark: COPY / DUPLICATE / PROVISIONAL
  Language: FR | EN      Paper: A4 | Letter     Copies: n
```
Portal downloads always use a rendition with digital signature enabled. All renditions
share the original's number, hash and QR.

### 18.4 QR payload (offline-verifiable)
- Content (JSON, then JWS compact with EdDSA/Ed25519, `kid` = signing key id):
```
{ "v":1, "iss":"<tenant>/<branch>", "kind":"REPORT", "num":"PV-NKC-2026-0412", "iat":1757548800,
  "sub":{"acc":"SOGECO","prj":"AF-2026-0031"}, "dg":{"n":6,"age":28,"mean":"22.4","u":"MPa"},
  "h":"<first 16 bytes of pdf_sha256, base64url>", "t":"<verify_token>" }
```
- Encoded in the URL fragment: `https://verify.<domain>/#<jws>` (fragment never reaches the
  server). QR error correction level M; version chosen automatically (≤ 33 for ~900 bytes).
- Offline verification: the verify PWA caches the JWKS of all branches; checks signature,
  displays fields for side-by-side comparison with the paper.
- Online: the page calls `GET /verify/{token}` (step 1) and `POST /verify/{token}/digest`
  with the short code (step 2).

### 18.5 Verification API
| Endpoint | Returns |
|---|---|
| `GET /verify/{token}` | issuer, branch, kind, number, issued_at, subject (account name, project title), status, superseded_by number, revoked reason |
| `POST /verify/{token}/digest {short_code}` | digest JSON; rate-limited (5/min/IP), attempts logged |
| `GET /verify/{token}/original` (authenticated, scope OWN_ACCOUNT or staff) | the canonical PDF |
| `GET /verify/keys` | JWKS of active and recently retired keys |
| `GET /verify/transparency/head` | current tree head, size, timestamp, signature |
| `POST /verify/{token}/report-suspicious` | opens a fraud case with uploaded file |

### 18.6 Detection
Alerts (notification rules): ≥ 10 unknown tokens from one IP in 10 min; any lookup of a
REVOKED document; a document verified > N× the branch median; suspicious-document reports.
A fraud case queue exists in the back-office (Branch manager).

### 18.7 Key management
Signing keys are created and held in a KMS/HSM (cloud KMS by default); the API holds only a
signer handle. One key pair per branch per purpose (QR: Ed25519; PDF: RSA-3072 with an
X.509 certificate chained to the tenant root). Rotation with 90-day overlap; public keys
published; old signatures remain valid (LTA). Compromise of the application server must not
allow signing: signing calls require a service identity distinct from the API's.

### 18.8 Transparency log
Append-only Merkle log of `(issued_document_id, content_hash, issued_at)`; tree head signed
and published daily on the verification site; inclusion proof endpoint. No public blockchain.

### 18.9 Issuing external deliverables through the pipeline
Studies and some field services produce reports written outside the platform (Word, CAD,
third-party lab). These are issued the same way: upload the final PDF on the work order
phase or project → the pipeline converts to PDF/A-3, stamps a verification page (or a
footer band on each page: number, date, QR, short code), seals it, creates the
`issued_document`, stores the hash, notifies the client. External deliverables therefore
carry the same authenticity guarantees as generated reports. A phase may be configured as
`requires_deliverable`, blocking completion until one is issued.

### 18.10 E-signature provider interface
```
interface ESignProvider
  createEnvelope(document, signers[] {name, email, phone, role}, options) → {envelopeId, signingUrls[]}
  handleWebhook(rawBody, signature) → EnvelopeEvent{envelopeId, status, signerEvents[]}
  downloadSignedDocument(envelopeId) → pdfBytes, completionCertificate
  cancel(envelopeId)
```
Shipped with `manual` (paper scan) and a `mock` provider for tests; real providers are
configured per tenant in Integrations. The signed PDF returned by a provider is sealed by
our pipeline as well (nested signatures are valid in PAdES).

### 18.11 Printing architecture
- **Documents**: rendered PDFs open in the in-app viewer; the browser print dialog prints
  them; no special agent.
- **Labels**: two paths. (a) PDF label sheets for any printer. (b) Thermal label printers
  (Zebra/ZPL, TSC/TSPL): the worker renders ZPL and sends it directly to a network printer
  reachable from the server, or the tablet uses the **print bridge** — a small local agent
  (Go binary, runs on a PC at reception) that polls `GET /v1/print-jobs?station=` and
  forwards jobs to USB/Bluetooth/network printers. Stations and printers are configured
  per branch (§10.9); every job is logged and reprintable.
- **Receipts** (payments, cash close): same as labels, on thermal receipt printers if present.

## 19. Notifications

### 19.1 Event catalogue (authoritative list; every event carries tenant, branch, actor, at, payload)
```
account.created  contact.created  portal_user.invited  portal_user.first_login
project.created  project.closed  work_item.created  work_item.flagged_variance  work_item.delivered
quote.created  quote.revision_created  quote.approval_requested  quote.approved  quote.sent
quote.negotiating  quote.suspended  quote.refused  quote.expired  quote.accepted  quote.cancelled
contract.generated  contract.sent  contract.signed  order.created  order.amended  order.completed
expected_intake.created  intake.registered  specimen.labelled  sample.registered  stage.changed
test_run.scheduled  test_run.assigned  test_run.due_tomorrow  test_run.overdue  test_run.started
measurement.recorded  test_run.measured  computed_value.overridden  test_run.validated  test_run.cancelled
report.draft_ready  report.issued  report.superseded  report.revoked  document.rendered  document.printed
milestone.instantiated  milestone.invoiceable  invoice.issued  invoice.sent  invoice.due_soon  invoice.overdue
invoice.paid  credit_note.issued  payment.recorded  payment.allocated  payment.reversed  payment_intent.succeeded
stock.reserved  stock.released  stock.moved  stock.below_threshold  rental.started  rental.due_soon  rental.late
rental.returned  transfer.dispatched  transfer.received  maintenance.due  maintenance.done
work_order.created  phase.completed  work_order.late  work_order.completed
verification.suspicious  verification.revoked_lookup  fraud_case.opened
user.invited  user.disabled  role.changed  config.changed  backup.completed  backup.failed  job.failed
```

### 19.2 Channels
E-mail (transactional SMTP provider), SMS (adapter; local aggregator), WhatsApp Business
Cloud API (templates pre-approved), in-app (SSE stream + inbox). Contact preferences per
channel; quiet hours per branch; digests (daily supervisor digest = rule with `digest.cron`
over a saved query).

### 19.3 Default rules shipped (editable)
| Event | Audience | Channels |
|---|---|---|
| quote.sent | client SIGNATORY + COMMERCIAL contacts | e-mail, WhatsApp |
| quote.accepted | quote owner, lab supervisors of involved departments, finance | in-app, e-mail |
| intake.registered | client TECHNICAL contact | SMS/WhatsApp (short), portal |
| test_run.due_tomorrow | assigned technician, supervisor | in-app |
| report.issued | client TECHNICAL + COMMERCIAL contacts | e-mail (PDF link), WhatsApp, SMS (short), portal |
| invoice.issued / invoice.overdue | client ACCOUNTING contact | e-mail, WhatsApp |
| rental.late | assets staff, client contact | in-app, WhatsApp |
| verification.suspicious | branch manager | in-app, e-mail |
| daily digest 06:30 branch time | supervisors, branch manager | e-mail |

## 20. Audit and reporting

### 20.1 Audit
`audit_event(id, tenant_id, branch_id, aggregate_type, aggregate_id, action, actor_id, actor_type (USER, SYSTEM, CLIENT, API_KEY), at, before JSONB, after JSONB, context JSONB {ip, app, request_id})`.
Append-only (no UPDATE/DELETE grants for the application role). Every write path records it.
"History" tab everywhere reads it. Configuration changes are audited like data. Retention: forever.

### 20.2 Read models (materialised, refreshed by events or every 5 minutes)
`work_item_state`, `project_summary`, `account_balance`, `invoice_paid_status`, `stock_level`,
`department_daily_load`, `sales_pipeline`, `lab_throughput`, `receivables_ageing`.

### 20.3 Dashboards (KPIs per space)
| Space | KPIs and charts |
|---|---|
| Commercial | quotes by state, acceptance rate, quoted vs accepted amounts by period/category/service, ageing of negotiations, top accounts, pipeline funnel |
| Laboratory (per department) | intakes today, runs to do today (by technician), runs done, overdue, to review, specimens by stage/location, tomorrow's runs, turnaround (intake → report) median |
| Finance | invoiced vs collected by period, receivables ageing buckets (0–30, 31–60, 61–90, >90), cash position per treasury account, invoiceable-not-invoiced |
| Assets | stock by location, utilisation of rentable classes, active/late rentals, maintenance due, consumables below threshold |
| Delivery | work orders by state, progress, lateness, load per responsible |
| Tenant | all of the above across branches; per-branch comparison |
| Results analytics | project strength history, mix-design statistics, per-test dashboards, supplier comparison (§14.9) |
Every dashboard supports period, branch, department filters and export.

---

# PART IV — APPLICATIONS AND USER EXPERIENCE

## 21. Design system

### 21.1 Principles
1. **Data-dense, calm.** Neutral surfaces, one accent, colour reserved for meaning (state,
   action, alert). No decorative colour.
2. **One system, three apps.** The same tokens and components in back-office, admin and portal;
   the portal uses a lighter density.
3. **Tenant-themable.** Logo, primary colour and document header are tenant settings; the
   design system derives accessible shades automatically and validates contrast.
4. **Touch-first where it matters.** Laboratory screens designed for tablet first.
5. **Every state visible.** Loading skeletons, empty states with the next action, errors with
   recovery, offline banner, saved indicator.
6. **Fast by default.** Virtualised lists, optimistic updates where safe, prefetch on hover,
   route-level code splitting, ≤ 200 kB initial JS per app (gzipped) budget.

### 21.2 Tokens (default theme; tenant may override `primary` and logo)
| Token | Light | Dark | Use |
|---|---|---|---|
| `bg.canvas` | `#F6F7F9` | `#0B1220` | page background |
| `bg.surface` | `#FFFFFF` | `#111A2E` | cards, tables, dialogs |
| `bg.subtle` | `#EEF1F5` | `#182238` | table headers, hover rows |
| `border.default` | `#D9DEE7` | `#26324A` | borders, dividers |
| `text.primary` | `#111827` | `#E5E9F0` | body text |
| `text.secondary` | `#5B6472` | `#9AA5B5` | labels, help text |
| `text.inverse` | `#FFFFFF` | `#0B1220` | on primary |
| `primary` | `#1F5EFF` (default; Mizan tenant sets its brand orange, auto-adjusted to AA) | `#6D94FF` | primary actions, focus, links |
| `primary.hover` / `primary.subtle` | derived (−8 % L / 92 % tint) | derived | hover, selected backgrounds |
| `success` | `#12805C` | `#3CCB93` | validated, paid, delivered |
| `warning` | `#B26B00` | `#F5B342` | pending, due soon, to review |
| `danger` | `#C62828` | `#FF6B6B` | overdue, refused, revoked, delete |
| `info` | `#0E7490` | `#4FD1E5` | neutral notices |
| `focus.ring` | `primary` at 40 % alpha, 2 px | same | keyboard focus |
| Radius | 6 px controls, 10 px cards, 14 px dialogs | | |
| Shadow | 3 levels, low elevation | | |
| Spacing | 4-pt grid: 4, 8, 12, 16, 24, 32, 48 | | |

Workflow state colours are chosen by the admin from a fixed accessible palette of 12 hues
(each with light/dark variants) — never arbitrary hex.

### 21.3 Typography and icons
- UI font: **Inter** (variable), sizes 12/13/14/16/20/24/30, weights 400/500/600/700,
  tabular numerals in tables and amounts. Documents: an embedded font family (Inter or
  Noto Sans) guaranteeing accents and currency symbols.
- Icons: **Lucide** at 16/20 px; one icon per module fixed across apps.

### 21.4 Components
Buttons (primary, secondary, outline, ghost, danger; sm/md/lg; loading; icon-only with
tooltip), inputs (text, number with unit suffix, money with currency, date, date range,
select with search, multi-select with chips, checkbox, switch, radio group, textarea, file
drop, camera capture, QR scanner), data table (server pagination or virtual scroll, column
picker, resizable, pinned columns, row selection, bulk actions, expandable rows, footer
totals, saved views), KPI card, badge (state colour), timeline, kanban board, calendar
(day/week/month, drag-and-drop), stepper, dialogs (confirm, form, print options), drawer,
toasts, skeletons, empty states, breadcrumbs, tabs, accordion, tree, charts (bar, line, pie,
gauge, grading curve), PDF viewer, formula editor with validation and sandbox, permission
matrix grid, label preview, signature pad (for paper acceptance capture), command palette (⌘K).

### 21.5 Patterns
- **List page**: KPI strip → toolbar (search, filters, saved views, columns, export, import,
  new) → table → bulk action bar when rows selected.
- **Record page**: header (number, title, state badges, primary actions, `⋯` menu) → tabs
  (Details, related lists, Documents, Attachments, Comments, History) → right rail (key facts,
  graph links).
- **Form**: single column ≤ 640 px on tablet; sections; inline validation; autosave drafts;
  `Save`, `Save & new`, `Cancel`; unsaved-changes guard; double-submit lock.
- **Destructive action**: confirm dialog stating consequences ("3 scheduled runs will be
  cancelled"); soft delete with reason.
- **Print/export**: options dialog (§18.3); result opens in viewer with download/share.
- **Offline (tablet)**: banner; queued changes count; conflict list; manual sync button.

### 21.6 Responsive
| Breakpoint | Layout |
|---|---|
| ≥ 1280 | sidebar open, two-column record pages, dense tables |
| 768–1279 (tablet) | sidebar collapsed to icons, single-column forms, ≥ 44 px touch targets, numeric keypad inputs, scanner button in header |
| < 768 (phone) | bottom navigation, cards instead of tables, actions in sheet menus, portal optimised one-handed |
Print stylesheets for lists and records; official documents always via the pipeline.

### 21.7 Accessibility and i18n
WCAG 2.2 AA: contrast validated at build for tokens and at save for tenant primary; full
keyboard navigation; visible focus; labelled inputs; announced errors; reduced-motion
respected. UI and documents in **English and French**; per-user UI locale; per-account
document locale; per-branch defaults; number/date/currency formats by locale; RTL not
precluded (logical CSS properties only).

### 21.8 UX process (how "best UX" is produced, not hoped for)
- **Personas** maintained in the repo: Commercial (Aïcha, 30 quotes/week, phone-first),
  Reception (Moussa, tablet, gloves, noise), Technician (Sidi, at the press, one hand),
  Supervisor (Fatimetou, reviews 40 runs/day), Finance (Mohamed, statements and cash),
  Director (signs, reads dashboards on phone), Client site manager (Ahmed, WhatsApp, wants
  the PV now), Client accountant (invoices and receipts).
- **Journey maps** for the eight golden journeys (§Appendix S) with time-on-task targets:
  quote in < 5 min from an existing project; intake of 16 specimens in < 3 min; worksheet
  for 4 specimens in < 90 s; issue a report in < 60 s; record a payment in < 45 s.
- **Usability testing** every two weeks during Phases 1–3 with real staff on real devices,
  recorded and turned into tickets; a metric dashboard (task success, time, errors) is
  reviewed by the product owner.
- **Design reviews** on every screen against the checklist: primary action obvious, ≤ 7
  visible controls by default, state visible, error recoverable, works offline where
  required, keyboard complete, contrast validated, both languages fit without truncation.
- **Instrumentation**: anonymous UI analytics (screen timings, abandoned forms, rage
  clicks) feed the backlog; tenant may disable.

### 21.9 Interaction details that make the difference
- **Scan-first laboratory**: every lab screen accepts a scan at any time; scanning a label
  navigates to the right run/specimen without leaving context.
- **Smart defaults**: last used specimen type, ages, instrument, printer; project pre-filled
  from the last intake for the same delivery person; unit prices from the price list;
  payment terms from the default template.
- **Inline editing** in tables for quantities, prices and dates with undo; bulk edit for
  selected rows; **saved views** per user and shared per role.
- **Command palette (⌘K / Ctrl+K)** for navigation and actions ("new intake", "issue report
  PV-0412", "open project AF-2026-0031"); global search results grouped by type with
  keyboard navigation.
- **Optimistic UI** for low-risk actions (assign, stage change), with rollback on failure;
  explicit confirmation for money and issuance.
- **Progressive disclosure**: advanced options behind "More"; commercial fields hidden
  entirely (not greyed) when the field group is absent.
- **Notifications** are actionable: "Report ready to review → Review" opens the exact run.
- **Tablet ergonomics**: large numeric keypad, next-field on Enter, sticky action bar,
  landscape and portrait layouts, high-contrast mode for bright rooms, glove-friendly targets.
- **Perceived performance**: skeletons within 100 ms, data within 1 s, background prefetch
  of the next likely screen, PDF preview streamed while sealing finishes.
- **Zero dead ends**: every empty state, error and 404 offers the next action and search.
- **Onboarding**: first-run tour per role, contextual tips dismissible per user, a
  "What's new" panel per release.

## 22. Back-office

### 22.1 Shell
Sidebar (spaces and menus from permissions), top bar (global search ⌘K, branch switcher if
several, notifications inbox with SSE live updates, help, user menu: profile, locale, theme,
sign out), breadcrumbs, content, offline banner, scan button on tablet.

### 22.2 Home
Cards for authorised spaces; "My day": runs assigned to me, quotes awaiting my approval,
invoices to issue, alerts; recent items; favourites; quick create (by permission).

### 22.3 Project page (tabs by permission)
| Tab | Content | Buttons |
|---|---|---|
| Overview | timeline, next due runs, alerts, KPIs | `Edit`, `Close project`, `Print summary` |
| Work breakdown | tasks → items with 3 state badges; amount columns only with `commercial` | `Add task`, `Add item`, `Create quote from unquoted items`, `Flag variance`, `Reorder` |
| Quotes & contracts (`commercial`) | revisions, states, acceptance evidence, contract | `New quote`, `New revision`, `Send`, `Record paper acceptance`, `Generate contract`, `Use as template` |
| Intakes & samples | expected vs received, specimens by stage/location | `New intake`, `Print labels`, `Change stage` |
| Tests | runs by state, project calendar | `Schedule`, `Assign`, `Open worksheet` |
| Reports | versions, status, verify link | `Issue`, `New version`, `Revoke`, `Print / Export`, `Send to client` |
| Invoices & payments (`financial`) | milestones, invoices, payments, balance | `Invoice milestones`, `Invoice progress`, `Record payment`, `Statement` |
| Assets | rentals, sales, outings | `New rental`, `Return`, `Outing note` |
| Delivery | work orders, phases, progress | `Assign`, `Complete phase` |
| Documents · Attachments · Comments · History | | |

### 22.4 Commercial space
| Screen | Content | Specific buttons |
|---|---|---|
| Dashboard | §20.3 KPIs | period, branch, department, `Export` |
| Accounts | list (number, name, tier, active projects, balance, last activity) | `New account`, `Merge duplicates`, `Create portal access` |
| Account page | identity, contacts (roles, channels, portal), projects, quotes, invoices, balance, activities | `Edit`, `Add contact`, `New project`, `New quote`, `Statement`, `Deactivate` |
| Contacts | cross-account list | `New contact`, `Invite to portal`, `Reset password` |
| Projects | list | `New project` |
| Quotes | all quotes (number, rev, account, project, total, state, age in state, owner) | `New quote`, bulk `Send`, `Remind` |
| Quote builder | left: project items + catalog search by category; centre: lines grouped by task (qty, unit price from price list, line discount, billable); right: live totals, global discount, tax, milestones with 100 % check, conditions, notes, validity, locale | `Save`, `Preview PDF`, `Submit for approval`, `Send`, `New revision`, `Use as template`, `Add PM line`, `Reorder` |
| Quote page | revisions with diff, acceptance, contract, order, documents, history | `Record paper acceptance`, `Send by e-mail / WhatsApp`, `Mark negotiating / suspended / refused`, `Generate contract`, `Print / Export` |
| Contracts | list/page | `Generate`, `Send for signature`, `Upload signed contract` |
| Orders | list/page (frozen lines, amendments, provisioning results) | `Create amendment` |
| Client requests | portal requests queue | `Convert to project / quote`, `Reply`, `Close` |

### 22.5 Laboratory space
| Screen | Content | Specific buttons |
|---|---|---|
| Dashboard (department) | today: intakes, runs to do by technician, done, overdue, to review, specimens by stage/location, tomorrow | `Daily digest PDF` |
| Intake (tablet, stepper) | 1 project & expected; 2 specimens/samples + intake fields + age distribution; 3 delivered-by, photos, summary | `Save`, `Print labels`, `Add unquoted (variance)`, `Reprint` |
| Intakes | list | `New intake` |
| Calendar | day/week/month per department, load, technicians, overdue, drag-drop | `Assign`, `Reassign`, `Shift (reason)`, `Print plan` |
| Test runs | list | `Open worksheet`, `Assign`, `Cancel (reason)` |
| Worksheet (tablet) | header, inputs by level, live computed values, rules, instrument, photos, remarks | `Scan label`, `Save`, `Mark measured`, `Specimen missing/damaged (reason)`, `Override value (permission, reason)` |
| Stages & locations | kanban of specimens/samples | `Change stage (scan)`, `Bulk move` |
| To review | measured runs, draft report preview, project history comparison | `Validate`, `Return to technician (reason)`, `Issue report`, `Issue and send` |
| Reports | list | `Print / Export`, `New version`, `Revoke`, `Send` |
| Tests (generated menu) | categories → active definitions → runs, recent results, per-test dashboard | `New run for a project` |
| Sample registry | samples with requested tests (items), stage, location | `Change stage`, `Print label` |

### 22.6 Finance space
| Screen | Content | Specific buttons |
|---|---|---|
| Dashboard | invoiced/collected, ageing, cash position, invoiceable-not-invoiced | `Export` |
| To invoice | triggered milestones, delivered-not-invoiced items, by account/project | `Invoice (selection)`, `Preview`, `Postpone (reason)` |
| Invoices | list/page | `Issue`, `Print / Export`, `Send`, `Credit note`, `Record payment`, `Remind` |
| Credit notes | list/page | `Issue` |
| Payments | list/page | `New payment`, `Allocate`, `Receipt PDF`, `Reverse (reason)` |
| Treasury | accounts, entries, transfers, cash reconciliation | `New entry`, `Transfer cash → bank`, `Close day` |
| Statements | per account/project | `Generate PDF`, `Send` |
| Dunning | overdue by level | `Send reminders`, `Suspend (reason)` |
| Reconciliation | provider intents vs payments | `Match`, `Flag` |

### 22.7 Assets space
| Screen | Buttons |
|---|---|
| Dashboard | — |
| Equipment (classes, units, condition, location, history) | `New`, `Set maintenance`, `Retire` |
| Stock by location (total/reserved/available, movements) | `Adjust (reason)`, `Stock count` |
| Consumables | `Receive`, `Issue`, `Set threshold` |
| Rentals (from orders; hand-over, return, penalties) | `Prepare`, `Hand over (rental note)`, `Return (condition)`, `Compute penalty` |
| Sales | `Deliver (sale note)` |
| Outings | `New`, `Partial return` |
| Transfers | `New`, `Validate`, `Dispatch`, `Receive (quantities)` |
| Maintenance | `Plan`, `Close` |
| Fleet (vehicles, fuel slips, fines, purchase orders, maintenance orders) | `New document`, `Print` |
| Calendar (reservations/returns), Alerts | `Mark handled` |

### 22.8 Delivery space
Dashboard; work orders (phases, responsibles, deadlines) with `Assign`, `Complete phase`,
`Replan (reason)`; responsibles with load.

## 23. Admin console

| Section | Screens | Key actions |
|---|---|---|
| Platform (operator only) | tenants, plans, tenant admins, signing keys, health (jobs, deliveries, backups) | `New tenant`, `Suspend`, `Rotate key` |
| Organisation | tenant profile & branding (logo, primary colour with live contrast check), branches (identity, currency, taxes, timezone, working days), departments, signatories, treasury accounts | `New branch (wizard)`, `Clone configuration` |
| Users & access | users, memberships, roles, **permission matrix** (resources × actions, cells = scope + field-group chips), "View as" | `Invite`, `Disable`, `Duplicate role`, `Retire role`, `Reset MFA` |
| Numbering | schemes per kind and branch, pattern editor with live preview, versions | `New scheme`, `Activate`, `Reserve numbers` |
| Vocabularies | all lists, translations, colours, order, "used by" | `Add`, `Translate`, `Retire` |
| Workflows | per kind: states (semantic, colour), transitions (permission, guards, effects), SLA, versions, simulator | `New version`, `Simulate` |
| Catalog | categories, services (kind, unit, prices), **test-definition editor** (inputs, computed, aggregates, rules, stages, intake fields, report columns) with **sandbox**, specimen types, sieve sets, natures, materials, phase templates, equipment classes | `New definition`, `Test in sandbox`, `Activate`, `New version` |
| Prices & taxes | price lists, prices, overrides, tax rules, rounding | `Import list`, `Duplicate for period` |
| Documents | templates per kind/locale, variables, preview with sample data, print profiles, watermarks | `New version`, `Approve`, `Preview` |
| Notifications | rules, message templates, channels/providers, delivery log | `Test send` |
| Portal | default features, welcome texts, terms | — |
| Integrations | e-mail, SMS, WhatsApp, payment providers, accounting export, object storage | `Test connection` |
| Audit | full log, filters, export | — |
| Setup wizard | departments → units → natures → definitions → services & prices → templates → numbering → workflows → roles → users; spreadsheet import at each step | `Next`, `Import` |

## 24. Client portal

| Screen | Content | Buttons |
|---|---|---|
| Home | open projects, pending quotes, latest reports, unpaid invoices, notifications | `Request a quote`, `Ask a question` |
| Projects | list → project page: work breakdown (execution, financial), intakes, scheduled tests, reports, invoices | — |
| Quotes | revisions, diff, comments, **Accept** (OTP), `Refuse (reason)`, `Upload signed quote`, `Download` | — |
| Reports | download (digitally signed), versions, `Verify authenticity` | — |
| Invoices & payments | invoices, status, statements, recorded payments, `Pay online` (when provider exists), `Request invoice` | — |
| Requests | history and replies | `New request` |
| Account | contacts & access (client admin), channel preferences, locale, password, MFA | — |
| History | full timeline with documents | — |

## 25. Verification site
Step 1: token (from QR or typed) → issuer, branch, kind, number, date, account, project,
status (CURRENT / SUPERSEDED by … / REVOKED). Step 2: short code → digest. Authenticated:
download original. Buttons: `Verify another`, `Report suspicious document`, `Offline mode`.
Publishes JWKS and the daily transparency head. Installable PWA with offline signature check.

---

# PART V — ARCHITECTURE AND ENGINEERING

## 26. Technology decisions

Criteria: development speed for a broad business domain, correctness (money, workflows,
permissions), first-class PostgreSQL, a document pipeline that is genuinely state of the
art (PDF/A + PAdES-B-LTA + KMS-held keys), responsive front-ends with offline support,
serverless-friendly runtime (small images, fast cold starts), low operating cost, and high
productivity with AI coding assistants.

**Decision: Python for the platform, TypeScript/React for the user interfaces.**

| Layer | Decision | Why this is the strongest choice here |
|---|---|---|
| Language / runtime | **Python 3.12+** | Most productive language for a rule-heavy business domain; unmatched libraries for the two hardest parts of this system: document generation/signing and data validation. |
| Web framework | **Django 5.x** (ORM, migrations, transactions, admin for operators, i18n, signals) with **Django Ninja** for the public API (Pydantic v2 models, OpenAPI 3.1 generated, async endpoints where useful) | Django's ORM + migrations + auth give the data layer, tenancy hooks and admin tooling out of the box; Ninja gives FastAPI-style typed, fast, documented endpoints inside Django. FastAPI alone would require rebuilding ORM, migrations, auth and admin. |
| ASGI server | **Granian** (Rust-based ASGI/WSGI server) or Uvicorn workers | High throughput per instance, low memory, good on serverless containers. |
| Database | **PostgreSQL 16** (managed) with **row-level security**, JSONB, full-text/trigram; **PgBouncer/connection pooling** in front | Same rationale as before; RLS enforced via `SET LOCAL app.tenant_id` in a request-scoped connection wrapper. |
| Tenancy | Row-level (shared schema) with RLS; `django-tenants`-style schema isolation available per very large tenant later | Cheapest and simplest to operate; RLS is the backstop. |
| Jobs / events | **Procrastinate** (PostgreSQL-backed, async task queue) for background work; outbox rows written in the business transaction; periodic tasks via Procrastinate's scheduler | No Redis/RabbitMQ to run; transactional enqueue; works on serverless. |
| Validation / schemas | **Pydantic v2** everywhere at the API boundary; typed settings | Fast, strict, generates OpenAPI. |
| Identity | **django-allauth** (accounts, MFA/TOTP, passkeys/WebAuthn, e-mail/SMS OTP, social/OIDC providers) + short-lived JWT for SPAs (`django-ninja-jwt`) with refresh rotation; staff realm and client realm separated by user type and tenant | Fully Python, no extra identity server to operate; enterprise SSO (OIDC/SAML) added later through allauth providers. |
| Authorisation | In-house engine (grants → scope predicates as ORM `Q` objects → field-group filtering in Pydantic serialisers), cached per user | Exact fit for the matrix; simple and fast. |
| Formula engine | **Custom safe evaluator over Python `ast`** (whitelisted nodes and functions, no attribute access to internals, time-bounded) with **Pint** for units | Deterministic, safe, unit-aware; expressions compiled once per definition version. |
| Document rendering | **WeasyPrint** (HTML/CSS → PDF, pure Python, embedded fonts, **PDF/A-3b and PDF/UA output natively**) | No browser needed: smaller images, faster cold starts, deterministic output; ideal for reports, quotes, invoices, labels. |
| PDF sealing / signatures | **pyHanko** — PAdES-B-LTA, RFC 3161 timestamps, LTV embedding, visible/invisible signatures, **KMS/PKCS#11/cloud signers** | The best open-source PAdES implementation available; keys never leave the KMS. |
| QR signing | **joserfc** (JWS, EdDSA) + **segno** (QR) | Standard, offline-verifiable. |
| Object storage | Cloudflare **R2** (S3 API, zero egress) or the cloud provider's storage | PDFs, attachments, backups. |
| Real-time | **Server-Sent Events** from Django (async view) with PostgreSQL LISTEN/NOTIFY | Simple, works behind serverless with long-request support. |
| Search | PostgreSQL full-text + trigram | Adequate; no extra service. |
| Caching | PostgreSQL + per-instance memory; optional managed Redis only if measured | Fewer moving parts. |
| Front-end | **TypeScript, React 19, Vite**, **TanStack Router/Query/Table/Virtual/Form**, **Tailwind CSS v4** with design tokens, **Radix UI** primitives (shadcn/ui), **i18next**, **ECharts**, **Workbox PWA + Dexie** (offline), **openapi-typescript / openapi-fetch** generated client, **Storybook** with axe | The strongest ecosystem for data-dense, responsive, accessible interfaces; offline PWA covers tablets and phones. |
| Monorepo | `backend/` (Python, **uv** for dependencies, **ruff** lint/format, **mypy** strict), `frontend/` (pnpm + Turborepo), `infra/` (Terraform) | One repository, atomic changes, one API client. |
| Testing | **pytest** + **pytest-django** + **factory_boy** + **hypothesis** (money and rounding) + **schemathesis** (API contract fuzzing) ; **Vitest** + **Playwright** ; **k6** budgets | Correctness where it matters most. |
| Observability | OpenTelemetry (Django/Ninja/psycopg instrumentation) → Grafana Cloud free tier; **Sentry** (API + SPAs); provider uptime checks | See everything. |

Rejected for this system: FastAPI-only (rebuilds the data layer and admin); Node/NestJS
(weaker document/signing ecosystem); Go (fast, but far slower to build this breadth, and
the Python document pipeline is superior); Java/Kotlin (V1 stack, heavier images and cold
starts on serverless); microservices (no measured need).

## 27. System architecture

### 27.1 Shape: modular monolith on serverless containers
```
                 Cloudflare (DNS, CDN, WAF, TLS, rate limiting, bot protection)
   ┌──────────────┬──────────────┬──────────────┬──────────────┐
   │ app.<domain> │admin.<domain>│client.<domain>│verify.<domain>│   Cloudflare Pages (static SPAs, immutable assets)
   └──────────────┴──────────────┴──────────────┴──────────────┘
                                   │ HTTPS
                          api.<domain> ──▶ Cloud Run service "api"  (Django + Ninja, Granian, min 1 / max N instances,
                                                                     request-based autoscaling, canary traffic splitting)
                                          Cloud Run service "worker" (Procrastinate workers: render, seal, notify, schedule,
                                                                     read models, imports; min 1 instance, CPU always on)
                                          Cloud Run job "scheduler"  (Cloud Scheduler → periodic tasks: due/overdue, digests,
                                                                     dunning, reconciliation, backups verify, transparency publish)
                                   │
   ┌───────────────────────────────┼───────────────────────────────────────────────────┐
   │ Cloud SQL for PostgreSQL 16   │  Cloudflare R2 (documents, attachments)            │  Cloud KMS (signing keys)
   │ (HA, automated backups, PITR, │  Managed TSA (timestamp authority) — provider      │  Secret Manager (secrets)
   │  private IP + Auth Proxy /    │  E-mail (Postmark/Brevo) · SMS (aggregator) ·      │  Cloud Scheduler
   │  connection pooling)          │  WhatsApp Cloud API · e-sign provider · payments   │
   └───────────────────────────────┴────────────────────────────────────────────────────┘
```
- One Django project, one container image, three entrypoints (`api`, `worker`, `scheduler`).
- Modules are Django apps with public service interfaces; cross-app reads through
  services/read models; cross-app writes through domain events. `import-linter` enforces
  boundaries.
- Request path: JWT/session auth → tenant resolution (from token, validated against
  membership) → `SET LOCAL app.tenant_id` on the request connection → authorisation
  (grants → `Q` predicate, field groups) → service call inside `transaction.atomic()` →
  audit event + outbox job enqueued in the same transaction → Pydantic response.

### 27.2 Django apps and ownership
| App | Owns | Publishes | Subscribes |
|---|---|---|---|
| `identity` | users, memberships, roles, grants, api keys, sessions | user.*, role.changed | — |
| `org` | tenant, branch, department, signatory, treasury accounts, branding | config.changed | — |
| `config` | numbering, vocabularies, workflows, catalog, test definitions, specimen types, sieve sets, price lists, taxes, payment terms templates, templates, print profiles, notification rules | config.changed | — |
| `crm` | accounts, contacts, projects, participants, activities, client requests | account.*, project.*, contact.* | quote.accepted, report.issued |
| `project` | tasks, work items, work_item_state | work_item.* | order.created, intake.registered, report.issued, invoice.issued, payment.allocated |
| `sales` | quotes, revisions, lines, milestones, acceptances, contracts, orders, order lines, milestone instances | quote.*, order.*, contract.*, milestone.* | report.issued, work_item.delivered, invoice.issued |
| `lab` | expected intakes, intakes, specimens, samples, test runs, measurements, computed values, stage events, reports | intake.*, test_run.*, stage.changed, report.* | order.created, order.amended |
| `finance` | invoices, invoice lines, credit notes, payments, allocations, treasury entries, cash closes, payment intents, dunning | invoice.*, payment.*, credit_note.* | milestone.invoiceable, work_item.delivered, rental.late |
| `assets` | equipment, stock, movements, reservations, rentals, sales, outings, transfers, consumables, maintenance, fleet | stock.*, rental.*, transfer.*, maintenance.* | order.created, order.cancelled |
| `delivery` | phase templates, work orders, phases, assignments, responsibles | work_order.*, phase.completed | order.created |
| `documents` | issued documents, renditions, verification attempts, signing keys, transparency log, external deliverable issuance | document.*, verification.* | issue commands |
| `notify` | deliveries, preferences, channels | — | all events |
| `audit` | audit events | — | all writes |
| `analytics` | read models, dashboards | — | events |

### 27.3 API design
- REST + JSON via Django Ninja routers per app; OpenAPI 3.1 at `/api/openapi.json`;
  versioned prefix `/api/v1`; generated TypeScript client in CI.
- Resource naming and action sub-resources as in Appendix A (`POST /quotes/{id}/revisions/{n}:send`).
- Sparse fields, includes, filters, sorts, cursor pagination; `Idempotency-Key`;
  `ETag`/`If-Match` with `row_version`.
- `GET /me`, `GET /me/permissions`, `GET /events/stream` (SSE, async view, LISTEN/NOTIFY).
- Pydantic response models per role-visible field group (serialiser drops non-granted
  groups); request models ignore non-granted fields.
- Errors: RFC 9457 problem details with `message_key` and params; rate limits per tenant/IP.

### 27.4 Events, outbox, jobs
- Business write + `audit_event` + Procrastinate task (with `queueing_lock` = event id +
  handler) in one `transaction.atomic()`.
- Handlers idempotent; retries with exponential backoff; dead-letter visible in admin
  health; alerts on failures.
- Task kinds: `render_document`, `seal_document`, `send_notification`, `provision_order`,
  `schedule_runs`, `recompute_read_model`, `daily_digest`, `mark_due_and_overdue`,
  `reconcile_payments`, `import_spreadsheet`, `export`, `transparency_publish`,
  `backup_verify`, `purge_drafts`.

### 27.5 Offline worksheet protocol
Unchanged in substance: local queue (Dexie) of operations with `client_op_id`, ordered
sync to `POST /api/v1/sync/measurements`, per-op applied/rejected results, conflicts
surfaced, server-side re-validation of transitions. The service worker caches the
technician's runs for today and tomorrow with their definitions and labels.

### 27.6 Tenancy enforcement
- RLS policies on all tenant tables; the application DB role cannot bypass RLS; migrations
  use a privileged role.
- A connection wrapper sets `app.tenant_id` per request/task; a test asserts every model
  in tenant apps has the policy.
- Branch scoping via `Q` predicates from grants.

### 27.7 Performance
- Budgets (§1.4) enforced by k6 in CI on seeded data (10 k accounts, 50 k projects,
  500 k specimens). Python read paths use `select_related`/`prefetch_related`, annotated
  querysets and read models; no N+1 (checked by `nplusone` in tests).
- Cloud Run autoscaling by concurrency (target 40 concurrent requests per instance);
  min 1 instance for the API to avoid cold starts during working hours (scheduled scaling
  to 0 at night is optional); worker min 1.
- Static apps on Cloudflare Pages with immutable asset caching; API responses compressed.
- Documents rendered asynchronously; previews streamed; PDF templates cached.

### 27.8 Scale path (configuration, not code)
1. Start: api min1/max10, worker min1/max5, Cloud SQL 2 vCPU/8 GB HA, R2, KMS.
2. Growth: raise max instances; add read replica for analytics; enable Cloud SQL
   connection pooling; split worker queues (documents vs notifications) into separate
   services.
3. Large tenants: route a tenant to its own database via the tenant→DSN map; regional
   deployment in a second region behind Cloudflare load balancing if needed.

## 28. Security
- Authentication: allauth sessions for browsers with HttpOnly/SameSite cookies, or JWT for
  SPAs with 15-minute access tokens and rotating refresh tokens; MFA mandatory for staff
  roles holding `issue`, `sign`, `configure`, `allocate_payment`; passkeys supported;
  step-up authentication before signing, grant changes and key operations.
- Client users: staff-created, temporary password, forced change, optional MFA, OTP for
  quote acceptance; lockout and rate limits.
- Authorisation in API and database (§9.4, §27.6); field groups in serialisers.
- Secrets in Secret Manager; no secrets in the repository; automatic rotation where
  supported.
- TLS 1.3 at Cloudflare and between Cloudflare and Cloud Run; HSTS; CSP; CORS restricted
  to the four app origins; WAF managed rules; bot protection on verify and login.
- Uploads: content sniffing, size limits, antivirus scanning (ClamAV in the worker image or
  a scanning API), image re-encoding, private buckets with signed URLs.
- Dependency and image scanning (pip-audit, npm audit, Trivy); SBOM; Dependabot.
- Audit log immutable; admin actions step-up; data export and anonymisation per §8.
- Backups: Cloud SQL automated backups + PITR (7–35 days), R2 versioning, monthly restore
  drill into a staging instance recorded by the `backup_verify` task.
- Signing keys in Cloud KMS (HSM-backed level available); separate service account for the
  signing path; rotation runbook; transparency log for forensics.

## 29. Infrastructure, CI/CD, operations

### 29.1 Why not a VPS
A single VPS concentrates availability, backups, patching and scaling on one machine and one
person. Managed serverless containers give automatic TLS, autoscaling from zero, revision
based zero-downtime deploys with traffic splitting, regional redundancy, managed PostgreSQL
with point-in-time recovery, and pay-per-use pricing that is lower than a VPS at this
load. Operations become configuration in Terraform.

### 29.2 Target platform
| Component | Choice | Region / notes |
|---|---|---|
| API and worker | **Google Cloud Run** services (or Cloud Run jobs for one-off tasks) | `europe-west9` (Paris) or `europe-southwest1` (Madrid): lowest latency to Nouakchott among managed regions |
| Database | **Cloud SQL for PostgreSQL 16**, HA, automated backups, PITR, private IP, built-in connection pooling | Same region |
| Static apps | **Cloudflare Pages** | Global CDN |
| Edge | **Cloudflare** DNS, TLS, WAF, rate limiting, bot management | Global |
| Object storage | **Cloudflare R2** (S3 API, no egress fees) | EU jurisdiction setting |
| Secrets, keys | **Secret Manager**, **Cloud KMS** | Same project |
| Scheduling | **Cloud Scheduler** → Cloud Run job/endpoint | — |
| E-mail / SMS / WhatsApp | Postmark or Brevo; local SMS aggregator via adapter; Meta WhatsApp Cloud API | — |
| Observability | Cloud Logging/Monitoring + OpenTelemetry export to Grafana Cloud; Sentry | — |
| IaC | **Terraform** (project, services, SQL, KMS, secrets, IAM, scheduler, Cloudflare) | Reviewed in PRs |

**Alternative with equivalent properties**: AWS (App Runner or ECS Fargate + RDS PostgreSQL
+ S3 + KMS + EventBridge Scheduler) in `eu-west-3` (Paris), or **Fly.io** machines + managed
PostgreSQL (Neon/Supabase) for a smaller bill with slightly less managed depth. The
architecture is identical; only Terraform modules change.

### 29.3 Cost (indicative, monthly, at baseline load)
| Item | Estimate |
|---|---|
| Cloud Run api (min 1 instance, 1 vCPU/1 GB, ~2 M requests) | $25–45 |
| Cloud Run worker (min 1, CPU always allocated) | $20–35 |
| Cloud SQL PostgreSQL (2 vCPU/8 GB, HA, 50 GB, backups) | $90–140 (non-HA ≈ half) |
| Cloudflare Pages, DNS, WAF basics, R2 (50 GB) | $0–10 |
| Cloud KMS keys, Secret Manager, Scheduler, logging | $5–15 |
| E-mail/SMS/WhatsApp | usage |
| **Total** | **≈ $150–250** with HA database; ≈ $90–150 without HA. Scales with usage, no idle servers to patch. |

### 29.4 Environments and pipeline
`dev` (local Docker Compose: PostgreSQL, MinIO, Mailpit, worker), `staging` (own Cloud
project or namespace, smaller SQL, auto-deploy from `staging`), `production` (deploy on
tag/approval from `main`).
```
on push: ruff + mypy + eslint + tsc → pytest (with PostgreSQL service, RLS tests, authz matrix) → vitest →
         build image (multi-stage, distroless-python) → push to Artifact Registry → schemathesis contract run →
         Playwright e2e on an ephemeral Cloud Run revision (tagged, no traffic) → k6 smoke →
         staging deploy (100 % traffic) → production deploy: run migrations (Cloud Run job, expand/contract) →
         deploy new revision with 10 % traffic → automated checks (error rate, p95) 10 min → 100 % → old revision kept for instant rollback
```
Rollback = shift traffic to the previous revision (seconds). Migrations are backward
compatible within a release.

### 29.5 Backups and recovery
Cloud SQL automated daily backups + PITR; R2 object versioning; nightly logical dump
exported to R2 (cross-provider copy); monthly automated restore drill into staging with
integrity report (row counts, issued-document hash sample). RPO ≤ 5 min (PITR), RTO ≤ 1 h.

### 29.6 Observability
Structured JSON logs with request id and tenant; traces for requests and tasks; metrics
(latency per route, task durations, queue depth, delivery rates, verification attempts);
dashboards; alerts (error rate, p95 over budget, failed tasks, backup failures, certificate
and key expiry, budget thresholds).

## 30. Testing strategy
| Level | Scope | Tooling |
|---|---|---|
| Unit | totals and rounding (property-based), derived states, formula engine, numbering, workflow engine, permission resolution, milestone templates | pytest, hypothesis |
| Integration | each app's API against PostgreSQL with RLS; authz matrix generated from the permission grid (Appendix T); outbox/task delivery | pytest-django, factory_boy, PostgreSQL service |
| Documents | golden PDFs per template (text layer compare), PDF/A validation (veraPDF in CI), PAdES validation with an independent validator (pyHanko validate + external), QR round-trip offline | CI job |
| Contract | OpenAPI schema compatibility and fuzzing | schemathesis, oasdiff |
| E2E | golden paths (Appendix S) on the three apps and the verify site; offline worksheet scenario | Playwright |
| Performance | budgets on seeded data; cold-start budget on Cloud Run | k6 |
| Security | dependency/image scans; authz fuzzing (every endpoint × every role); RLS assertion per model | pip-audit, Trivy, custom |

## 31. Repository structure
```
/                          pyproject.toml (uv workspace), pnpm-workspace.yaml, turbo.json, Makefile, docker-compose.dev.yml
/backend
  /config                  settings (pydantic-settings), asgi.py, urls.py
  /platform                db (tenant connection wrapper, RLS), auth (allauth, JWT), authz (grants → Q, field groups),
                           events (outbox), tasks (Procrastinate), storage (R2/S3), i18n, telemetry, formula (ast evaluator, units)
  /apps/{identity,org,config,crm,project,sales,lab,finance,assets,delivery,documents,notify,audit,analytics}
      each: models.py, schemas.py (Pydantic), services.py, api.py (Ninja router), events.py, tasks.py, migrations/, tests/
  /templates/documents     default HTML/CSS templates (seed) ; /templates/messages (e-mail/SMS/WhatsApp seeds)
  /seeds                   demo tenant, roles, workflows, numbering, four test definitions, payment terms templates
/frontend
  /apps/{back-office,admin,portal,verify}
  /packages/{ui,tokens,api-client,i18n,offline,charts,formula-editor}
/infra                     terraform/ (gcp + cloudflare modules), k6/, grafana/, runbooks/
/docs                      this specification, ADRs, personas, journey maps
```
Conventions: Conventional Commits; ADR per decision; `import-linter` contracts between apps;
`ruff`, `mypy --strict`, `eslint`, `tsc` gate every PR; seed command creates a complete demo
tenant.

# PART VI — DELIVERY

## 32. Build plan

Strangler approach: V1 stays live until each slice is taken over. No data migration.
Each epic lists tickets with acceptance criteria (AC). Estimates assume 2 backend, 2
frontend, 1 QA/designer, 1 product owner.

### Phase 0 — Platform foundations (8 weeks)
| Epic | Tickets (AC in brackets) |
|---|---|
| E0.1 Repository & CI | monorepo skeleton; lint/test/build pipelines; image builds; ephemeral e2e stack (AC: green pipeline on empty apps) |
| E0.2 Infrastructure | Terraform for Cloud Run (api, worker, scheduler), Cloud SQL with PITR, KMS, Secret Manager, R2, Cloudflare DNS/Pages/WAF; canary deploy with instant rollback; restore drill task; monitoring (AC: zero-downtime canary deploy demonstrated; restore verified) |
| E0.3 Database & tenancy | schema conventions, RLS policies, migration tooling, seed tenant (AC: cross-tenant read impossible in tests) |
| E0.4 Identity | django-allauth (MFA, passkeys, OTP), JWT for SPAs, staff and client user types, staff-created client accounts with forced password change (AC: login/logout/MFA in each app; client onboarding flow) |
| E0.5 Authorisation | grants model, resolver, scope predicates, field-group serialisation, `/me/permissions`, permission matrix UI, "view as" (AC: authz matrix test suite passes for default roles) |
| E0.6 Audit & events | audit_event, outbox, Procrastinate workers, SSE stream, history tab component (AC: every write audited; events delivered once) |
| E0.7 Configuration core | numbering engine + UI, vocabularies + UI, workflow engine + UI (semantics, guards, effects), payment terms templates, signatories and signature modes, branch settings (AC: admin creates scheme/vocab/workflow/payment terms/signatory without code; numbers unique under concurrency test) |
| E0.8 Documents core | template store, WeasyPrint renderer (PDF/A-3b), pyHanko PAdES-B-LTA sealing via KMS, signature modes (image/drawn/certificate/external), issued_document, QR signing, verify site steps 1–2, transparency log (AC: sample document verifies offline and online; altered PDF fails; veraPDF and PAdES validators pass) |
| E0.9 Notifications core | rules engine, e-mail channel, delivery log, in-app inbox (AC: rule fires on event; failures retried and alerted) |
| E0.10 Design system | tokens, theming, components, list/record/form patterns, app shells, i18n FR/EN (AC: Storybook with accessibility checks; contrast validated) |
| E0.11 Setup wizard | branch creation flow across configuration sections; spreadsheet imports (AC: new branch usable end to end in < 1 h) |

### Phase 1 — Commercial (12 weeks)
| Epic | Tickets |
|---|---|
| E1.1 CRM | accounts, contacts (roles, channels), portal access creation, duplicates/merge, activities, client requests |
| E1.2 Catalog & prices | categories, services with kinds, units, price lists, tax rules, imports |
| E1.3 Project & work breakdown | tasks, items, quantities, derived states read model, project page shell with permission-composed tabs |
| E1.4 Quotes | builder, revisions, totals, PM lines, milestones with rounding, conditions, PDF template, send, approval threshold, quote workflow |
| E1.5 Acceptance & orders | PORTAL OTP, PAPER scan, ESIGN adapter interface; order creation; provisioning of expected intakes and milestone instances; amendments; "use as template" |
| E1.6 Contracts | template, generation, signature evidence |
| E1.7 Commercial dashboard & portal (read + accept) | KPIs; portal home, projects, quotes with acceptance |
AC: all new quotes issued in V2; V1 quote screens read-only; acceptance evidence visible to client.

### Phase 2 — Laboratory (16 weeks)
| Epic | Tickets |
|---|---|
| E2.1 Test-definition engine | schema, versioning, formula engine integration, sandbox UI, specimen types, sieve sets, stages/locations |
| E2.2 Definitions | CONCRETE_COMPRESSION, BLOCK_COMPRESSION, SIEVE_ANALYSIS, WATER_CONTENT seeded; quality lead adds others |
| E2.3 Intake | tablet stepper, expected intakes, specimens/samples, age distribution validation, variances, labels (ZPL/PDF), reprint |
| E2.4 Scheduling | run creation rules, calendar, assignment, capacity, due/overdue jobs |
| E2.5 Worksheet | generated forms, live computation, rules, overrides, photos, offline sync protocol, scan |
| E2.6 Review & reports | review queue, draft rendering, issuance, versions, revocation, send, portal reports |
| E2.7 Lab dashboards & digest | department dashboard, stage/location kanban, daily digest rule |
AC: a PV produced end to end from a tablet with no paper; a new test defined and used without a release; offline worksheet syncs correctly after reconnection.

### Phase 3 — Finance & full portal (12 weeks)
| Epic | Tickets |
|---|---|
| E3.1 Invoicing | to-invoice queue, milestone and progress invoices, gap-free numbering, PDF, send, credit notes |
| E3.2 Treasury & payments | accounts, entries, payments, allocations, receipts, cash reconciliation, statements |
| E3.3 Dunning & reconciliation | schedules, reminders, provider intents, reconciliation queue, manual provider |
| E3.4 Portal complete | invoices, payments, requests, account management, history, notifications preferences |
| E3.5 Finance dashboard | ageing, cash position, collected vs invoiced |
AC: invoices only from V2; first external client active on portal; Mizan Caisse replaced by treasury.

### Phase 4 — Assets & delivery (12 weeks)
| Epic | Tickets |
|---|---|
| E4.1 Stock & equipment | classes, units, locations, levels from movements, adjustments, counts |
| E4.2 Rentals & sales | from orders, reservations, hand-over/return notes, penalties → invoiceable |
| E4.3 Outings, transfers, consumables, maintenance, fleet | all documents and workflows |
| E4.4 Delivery | phase templates, work orders, assignments, progress, lateness |
| E4.5 Dashboards | assets and delivery |
AC: V1 decommissioned.

### Phase 5 — Continuous
Payment providers as APIs arrive; analytics; second branch/tenant by configuration; WhatsApp
template expansions; native wrappers if store presence is desired.

Indicative total: **12–15 months** to full parity with portal; commercial value after Phase 1.

## 33. Coding rules and definition of done

### 33.1 Rules
1. No business strings in domain code: labels, number formats, prices, recipients,
   formulas, state names. Enforced by a lint on `internal/modules/**` (string literal
   allow-list) and code review.
2. New lifecycle kinds register their semantics with the workflow engine; no free `status`
   columns.
3. Every endpoint declares `(resource, action)` and is covered by generated authz tests.
4. Every state change emits an audit event; consequences are subscribers.
5. Every document goes through the documents module; no client-side PDF for official documents.
6. Money `NUMERIC` with currency; business dates `DATE`; instants UTC.
7. Every list paginated; every update uses `row_version`; counters/stock atomic.
8. Every UI string in FR and EN; every configurable label translatable.
9. Every module ships list, record, form, dashboard, export, permissions, events, and
   guard/effect documentation.
10. Migrations expand/contract; never destructive in the same release.
11. Performance budgets are tests; a regression fails CI.

### 33.2 Definition of done (per feature)
Code reviewed · unit and integration tests green · e2e for the golden path · authz tests
generated and green · events and history visible · FR/EN strings · admin configuration for
anything variable · dashboard/list/export where applicable · one-page user doc per screen ·
deployed to staging and accepted by the product owner · performance budget respected.

## 34. Glossary (UI French ⇄ code English)
Client = Account · Contact = Contact · Projet/chantier = Project · Tâche = Task · Élément =
WorkItem · Prestation/service = Service · Devis = Quote · Révision = QuoteRevision · Ligne =
QuoteLine · Modalité/jalon = Milestone · Acceptation = Acceptance · Contrat = Contract ·
Commande = Order · Avenant = Amendment · Réception = Intake · Éprouvette = Specimen ·
Échantillon = Sample · Essai (définition) = TestDefinition · Essai planifié = TestRun · Mesure
= Measurement · Valeur calculée = ComputedValue · Étape/lieu = Stage/Location · Rapport/PV =
Report · Émission = IssuedDocument · Rendu = Rendition · Facture = Invoice · Avoir = CreditNote
· Paiement = Payment · Affectation = PaymentAllocation · Caisse/banque = TreasuryAccount ·
Écriture = TreasuryEntry · Location = Rental · Vente = Sale · Bon de sortie = Outing ·
Transfert = Transfer · Équipement = Equipment · Emplacement = StockLocation · Modèle de phases
= PhaseTemplate · Ordre de travail = WorkOrder · Agence = Branch · Service (département) =
Department · Signataire = Signatory · Schéma de numérotation = NumberingScheme · Pour mémoire
= non-billable line · Écart = Variance · Locataire (plateforme) = Tenant.

## 35. Decisions taken and default assumptions

| Topic | Decision |
|---|---|
| Accreditation | Not in scope; audit trail and equipment register kept for paperless operation |
| Tenancy | Multi-tenant from day one (tenant → branch → department); Mizan is tenant #1 with one branch |
| Languages | English and French; RTL not precluded |
| Client accounts | Created by staff; no self-signup |
| Quote acceptance | Portal with OTP, paper scan, e-signature adapter |
| Signature on documents | Approval once; renditions with print options; portal copies digitally signed |
| Document security | Signed QR (JWS/EdDSA) + online registry + PAdES-B-LTA + transparency log; keys in KMS |
| Payments | Manual recording now; provider adapters when APIs exist; finance in one module (Mizan Caisse absorbed) |
| Migration | None; V1 history stays in V1 |
| Concrete outlier rule | Single specimen ≥ 5 MPa below rounded mean excluded and recomputed; two or more → flag only; threshold configurable |
| Block bearing surfaces | Derived from geometry per type with tracked overrides |
| Hosting | Serverless managed: Cloud Run + Cloud SQL (PITR) + Cloudflare (Pages, DNS, WAF, R2) + Cloud KMS; Terraform; canary deploys; AWS or Fly.io as equivalent alternatives |
| Technology | Python (Django + Django Ninja, WeasyPrint + pyHanko, Procrastinate) + PostgreSQL + React/TypeScript per §26 |
| Volumes assumed | ≤ 500 quotes, ≤ 1 000 intakes, ≤ 10 000 specimens, ≤ 50 users per branch per month; architecture tested at 10× |
| Team and timeline | 5–6 people; 12–15 months to parity |

Open items that do not block the build (defaults apply until answered): exact sales volume
per test (ordering of Phase 2 definitions); in-country key custody requirement (else cloud
KMS); SMS/WhatsApp aggregators available in Mauritania; whether the public digest exposure
behind the short code is acceptable to all clients (default: yes, per-tenant switch exists).

---

# PART VII — APPENDICES (BUILD REFERENCE)

## Appendix A — API catalogue (v1)

All routes under `/v1`, tenant resolved from the token, branch from `X-Branch-Id` header
(validated against memberships). `(resource.action)` is the declared permission.

### A.1 Session and platform
| Method & path | Permission | Notes |
|---|---|---|
| GET /me | — | profile, memberships, locale |
| GET /me/permissions | — | effective grants per membership |
| GET /events/stream | — | SSE: notifications, entity change hints |
| GET /openapi.json | — | spec |
| GET /health, /ready | — | liveness/readiness |

### A.2 Organisation and configuration
| Method & path | Permission |
|---|---|
| GET/POST /branches, GET/PATCH /branches/{id} | branch.view / branch.configure |
| GET/POST /departments, PATCH /departments/{id} | department.configure |
| GET/POST /signatories, PATCH /signatories/{id} | branch.configure |
| GET/POST /numbering-schemes, POST /numbering-schemes/{id}:activate, GET /numbering-schemes/{id}/preview, POST /numbering-schemes/{id}/reservations | numbering_scheme.configure |
| GET/POST /vocabularies/{kind}/entries, PATCH /vocabularies/{kind}/entries/{id}, POST …:retire | vocabulary.configure |
| GET/POST /workflows, GET /workflows/{id}, POST /workflows/{id}/versions, POST /workflows/{id}:activate, POST /workflows/{id}:simulate | workflow.configure |
| GET/POST /service-categories, PATCH /service-categories/{id} | service_category.configure |
| GET/POST /services, PATCH /services/{id}, POST /services/{id}:retire | service.configure |
| GET/POST /test-definitions, GET /test-definitions/{id}, POST /test-definitions/{id}/versions, POST /test-definitions/{id}:activate, POST /test-definitions/{id}:sandbox | test_definition.configure |
| GET/POST /specimen-types, /sieve-sets, /phase-templates, /equipment-classes | *.configure |
| GET/POST /price-lists, POST /price-lists/{id}/prices:import, GET /prices/resolve?service&account&date | price_list.configure / view |
| GET/POST /tax-rules | tax_rule.configure |
| GET/POST /document-templates, POST /document-templates/{id}/versions, POST …:approve, POST …:preview | document_template.configure |
| GET/POST /print-profiles | document_template.configure |
| GET/POST /notification-rules, /message-templates, POST /notification-rules/{id}:test | notification_rule.configure |
| GET/POST /integrations, POST /integrations/{id}:test | integration.configure |
| GET /audit-events?filter… | audit_event.view |

### A.3 Identity
| Method & path | Permission |
|---|---|
| GET/POST /users, PATCH /users/{id}, POST /users/{id}:disable, POST /users/{id}:reset-mfa | user.* |
| GET/POST /memberships, DELETE /memberships/{id} | user.edit |
| GET/POST /roles, PATCH /roles/{id}, POST /roles/{id}:duplicate, POST /roles/{id}:retire | role.configure |
| PUT /roles/{id}/grants | role.configure |
| GET /users/{id}/effective-permissions | user.impersonate_view |

### A.4 CRM
| Method & path | Permission |
|---|---|
| GET/POST /accounts, GET/PATCH /accounts/{id}, POST /accounts/{id}:merge, GET /accounts/{id}/statement | account.* |
| GET/POST /contacts, PATCH /contacts/{id}, POST /contacts/{id}:invite-portal, POST /contacts/{id}:reset-password | contact.* |
| GET/POST /projects, GET/PATCH /projects/{id}, POST /projects/{id}:close, GET /projects/{id}/summary | project.* |
| GET/POST /projects/{id}/participants | project.edit |
| GET/POST /activities | account.edit |
| GET/POST /client-requests, POST /client-requests/{id}:convert, POST …:reply, POST …:close | contact.view / project.create |

### A.5 Project and work breakdown
| Method & path | Permission |
|---|---|
| GET/POST /projects/{id}/tasks, PATCH /tasks/{id}, POST /tasks:reorder | task.* |
| GET/POST /projects/{id}/work-items, PATCH /work-items/{id}, POST /work-items/{id}:flag-variance, DELETE /work-items/{id} | work_item.* |
| GET /projects/{id}/work-items/states | work_item.view |

### A.6 Sales
| Method & path | Permission |
|---|---|
| GET/POST /quotes, GET /quotes/{id} | quote.* |
| POST /quotes/{id}/revisions (from unquoted items or copy), GET /quotes/{id}/revisions/{n}, PATCH /quotes/{id}/revisions/{n} (draft only) | quote_revision.edit |
| PUT /quotes/{id}/revisions/{n}/lines, PUT …/milestones | quote_revision.edit |
| POST /quotes/{id}/revisions/{n}:submit, :approve, :send, :negotiate, :suspend, :refuse, :cancel | quote.submit / approve / … |
| GET /quotes/{id}/revisions/{a}/diff/{b} | quote.view |
| POST /quotes/{id}/revisions/{n}/acceptances (PAPER, ESIGN) | acceptance.create |
| POST /quotes/{id}/revisions/{n}:use-as-template {target_project_id} | quote.create |
| GET/POST /contracts, POST /contracts/{id}:send, POST /contracts/{id}:record-signature | contract.* |
| GET /orders, GET /orders/{id}, POST /orders/{id}/amendments | order.* |
| GET /orders/{id}/milestone-instances | order.view |

### A.7 Laboratory
| Method & path | Permission |
|---|---|
| GET /projects/{id}/expected-intakes | expected_intake.view |
| GET/POST /intakes, GET/PATCH /intakes/{id}, POST /intakes/{id}:print-labels | intake.* |
| GET /specimens/{id}, POST /specimens/{id}:change-stage, POST /specimens/{id}:mark-missing | specimen.* |
| GET /samples/{id}, POST /samples/{id}:change-stage | sample.* |
| GET /labels/{token} (resolve) | specimen.view |
| GET /test-runs?filter, GET /test-runs/{id}, POST /test-runs/{id}:assign, :start, :measure, :cancel | test_run.* |
| GET /test-runs/{id}/worksheet (generated form) | test_run.view |
| PUT /test-runs/{id}/measurements (batch), POST /sync/measurements (offline batches) | measurement.edit |
| POST /test-runs/{id}/computed-values/{key}:override | test_run.override_computed_value |
| POST /test-runs/{id}:validate, :return | test_run.review_results |
| GET /calendar?department&from&to, POST /calendar:reschedule | test_run.assign |
| GET/POST /reports, GET /reports/{id}, POST /reports:draft {run_ids}, POST /reports/{id}:issue, :new-version, :revoke, :send | report.* |
| GET /departments/{id}/dashboard | dashboard.view |

### A.8 Finance
| Method & path | Permission |
|---|---|
| GET /to-invoice | invoice.view |
| GET/POST /invoices, GET /invoices/{id}, POST /invoices/{id}:issue, :send, :cancel | invoice.* |
| GET/POST /credit-notes, POST /credit-notes/{id}:issue | credit_note.* |
| GET/POST /payments, POST /payments/{id}/allocations, POST /payments/{id}:reverse, GET /payments/{id}/receipt | payment.* |
| GET/POST /treasury-accounts, GET/POST /treasury-entries, POST /treasury:transfer, POST /treasury/{id}:close-day | treasury_*.* |
| GET /accounts/{id}/statement, GET /projects/{id}/statement | account.view(financial) |
| GET /dunning, POST /dunning:run, POST /invoices/{id}:suspend-dunning | invoice.edit |
| POST /payment-intents, POST /webhooks/payments/{provider} | payment.create / public with signature |
| GET /reconciliation, POST /reconciliation/{id}:match | payment.allocate_payment |

### A.9 Assets and delivery
| Method & path | Permission |
|---|---|
| GET/POST /equipment, PATCH /equipment/{id}, POST /equipment/{id}:set-state | equipment.* |
| GET /stock-levels, GET/POST /stock-movements, POST /stock:adjust, POST /stock:count | stock.* |
| GET/POST /consumables, POST /consumables/{id}:receive, :issue | consumable.* |
| GET /rentals, POST /rentals/{id}:prepare, :hand-over, :return, :compute-penalty | rental.* |
| GET /sales, POST /sales/{id}:deliver | sale.* |
| GET/POST /outings, POST /outings/{id}:return | outing.* |
| GET/POST /transfers, POST /transfers/{id}:validate, :dispatch, :receive | transfer.* |
| GET/POST /maintenance, POST /maintenance/{id}:close | maintenance.* |
| GET/POST /vehicles, GET/POST /fleet-documents | vehicle.* / fleet_document.* |
| GET/POST /work-orders, POST /work-orders/{id}/phases/{p}:assign, :complete, POST /work-orders/{id}:replan | work_order.* |
| GET/POST /responsibles | work_order.configure |

### A.10 Documents, verification, portal, misc
| Method & path | Permission |
|---|---|
| GET /documents/{id}, POST /documents/{id}/renditions {options}, GET /documents/{id}/renditions/{r} | *.print |
| GET /verify/{token}, POST /verify/{token}/digest, GET /verify/keys, GET /verify/transparency/head, POST /verify/{token}/report-suspicious | public (rate-limited) |
| Portal: GET /portal/home, /portal/projects, /portal/quotes/{id}, POST /portal/quotes/{id}:request-otp, :accept {otp}, :refuse, POST /portal/quotes/{id}/signed-upload, GET /portal/reports, /portal/invoices, POST /portal/requests | OWN_ACCOUNT scoped grants |
| POST /imports {kind, file}, GET /imports/{id} (report) | *.create |
| POST /exports {kind, filter}, GET /exports/{id} | *.export |
| GET/POST /attachments, GET /attachments/{id}/download | attachment.* |
| GET/POST /comments | comment.* |
| GET /search?q= | scoped by caller |

## Appendix B — Core schema (PostgreSQL DDL excerpts)

Naming: snake_case, singular tables, `_id` suffix, `chk_`/`uq_`/`idx_` prefixes. Every
tenant table includes the common columns of §8 (omitted below for brevity as `-- common`).

```sql
create table tenant (id uuid primary key, code text unique not null, name text not null,
  theme jsonb not null default '{}', status text not null default 'ACTIVE', created_at timestamptz default now());

create table branch (id uuid primary key, tenant_id uuid not null references tenant(id), code text not null,
  legal_name text not null, identifiers jsonb, address jsonb, currency char(3) not null, timezone text not null,
  locales text[] not null default '{fr,en}', rounding text not null default 'HALF_UP_2', working_days int[] not null,
  settings jsonb not null default '{}', -- common
  unique (tenant_id, code));
alter table branch enable row level security;
create policy tenant_isolation on branch using (tenant_id = current_setting('app.tenant_id')::uuid);

create table department (id uuid primary key, tenant_id uuid not null, branch_id uuid not null references branch(id),
  code text not null, colour text, active bool default true, unique (branch_id, code));

create table i18n_text (entity text not null, entity_id uuid not null, field text not null, locale text not null,
  text text not null, tenant_id uuid not null, primary key (entity, entity_id, field, locale));
create unique index uq_i18n_label on i18n_text (tenant_id, entity, field, locale, lower(text)) where field = 'label';

create table app_user (id uuid primary key, tenant_id uuid not null, idp_subject text unique not null, email citext not null,
  display_name text, locale text default 'fr', mfa_enrolled bool default false, status text default 'ACTIVE');
create table role (id uuid primary key, tenant_id uuid not null, code text not null, is_template bool default false, unique (tenant_id, code));
create table grant_ (id uuid primary key, role_id uuid not null references role(id), resource text not null, action text not null,
  scope text not null, field_groups text[] not null default '{}', unique (role_id, resource, action, scope));
create table membership (id uuid primary key, tenant_id uuid not null, user_id uuid not null references app_user(id),
  branch_id uuid references branch(id), department_id uuid references department(id), role_id uuid not null references role(id),
  account_id uuid, project_ids uuid[], status text default 'ACTIVE');

create table numbering_scheme (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, applies_to text not null,
  department_id uuid, pattern text not null, reset text not null, gap_policy text not null, allocation text not null,
  version int not null default 1, status text not null default 'DRAFT', effective_from date, immutable bool default false);
create table numbering_counter (scheme_id uuid references numbering_scheme(id), period_key text not null, value bigint not null default 0,
  primary key (scheme_id, period_key));
create table number_reservation (scheme_id uuid, number text, reserved_by uuid, reason text, primary key (scheme_id, number));

create table workflow (id uuid primary key, tenant_id uuid not null, branch_id uuid, kind text not null, version int not null, status text not null);
create table workflow_state (id uuid primary key, workflow_id uuid references workflow(id), code text not null, semantic text not null,
  colour text not null, is_initial bool default false, is_terminal bool default false, sla_days int, unique (workflow_id, code));
create table workflow_transition (id uuid primary key, workflow_id uuid references workflow(id), from_state_id uuid, to_state_id uuid,
  required_action text not null, guards text[] not null default '{}', effects text[] not null default '{}', ord int);

create table service_category (id uuid primary key, tenant_id uuid not null, parent_id uuid, code text not null, department_id uuid, ord int);
create table service (id uuid primary key, tenant_id uuid not null, category_id uuid references service_category(id), code text not null,
  department_id uuid, kind text not null check (kind in ('LAB_TEST','FIELD_SERVICE','STUDY','RENTAL','SALE','FEE')),
  unit_of_sale text not null, test_definition_id uuid, phase_template_id uuid, equipment_class_id uuid, stock_item_id uuid, active bool default true,
  unique (tenant_id, code));
create table test_definition (id uuid primary key, tenant_id uuid not null, code text not null, version int not null, status text not null,
  category_id uuid, department_id uuid, method_ref text, unit_under_test text not null, scheduling jsonb not null, stages jsonb not null,
  intake_fields jsonb not null default '[]', inputs jsonb not null, computed jsonb not null, aggregates jsonb not null default '[]',
  rules jsonb not null default '[]', required_equipment_class_id uuid, report_template_id uuid, report_columns jsonb, unit_of_sale text,
  locked bool default false, unique (tenant_id, code, version));
create table specimen_type (id uuid primary key, tenant_id uuid not null, code text not null, shape text not null, dims jsonb not null, derived jsonb);

create table account (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, number text not null, legal_name text not null,
  normalized_name text generated always as (lower(unaccent(legal_name))) stored, tax_id text, tier_id uuid, tax_exempt bool default false,
  document_locale text default 'fr', portal_features text[] default '{}', state_id uuid, unique (tenant_id, number));
create index idx_account_name_trgm on account using gin (normalized_name gin_trgm_ops);
create table contact (id uuid primary key, tenant_id uuid not null, account_id uuid references account(id), first_name text, last_name text,
  function_id uuid, phone text, whatsapp text, email citext, roles text[] default '{}', channel_prefs jsonb default '{}', portal_user_id uuid, active bool default true);
create table project (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, number text not null, account_id uuid references account(id),
  title text not null, location text, sites jsonb default '[]', owner_user_id uuid, planned_start date, planned_end date, state_id uuid, unique (tenant_id, number));
create table project_participant (project_id uuid references project(id), account_id uuid references account(id), role_id uuid, primary key (project_id, account_id, role_id));

create table task (id uuid primary key, tenant_id uuid not null, project_id uuid references project(id), title text not null, category_id uuid, priority_id uuid,
  due_date date, owner_user_id uuid, ord int);
create table work_item (id uuid primary key, tenant_id uuid not null, project_id uuid references project(id), task_id uuid references task(id),
  service_id uuid references service(id), quantity numeric(12,3) not null, unit text, specimen_type_id uuid, options jsonb default '{}', notes text,
  origin text not null default 'QUOTE', qty_expected numeric(12,3) default 0, qty_received numeric(12,3) default 0, qty_reported numeric(12,3) default 0,
  qty_invoiced numeric(12,3) default 0, delivered_at timestamptz);

create table quote (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, number text, project_id uuid references project(id),
  account_id uuid, currency char(3), locale text, conditions uuid[] default '{}', validity_days int, notes_client text, notes_internal text,
  owner_user_id uuid, state_id uuid, current_revision_no int default 1);
create table quote_revision (id uuid primary key, quote_id uuid references quote(id), revision_no int not null, frozen bool default false, frozen_at timestamptz,
  discount_type text default 'NONE', discount_value numeric(18,2) default 0, tax_rule_id uuid, subtotal numeric(18,2), discount_amount numeric(18,2),
  taxable numeric(18,2), tax_amount numeric(18,2), total numeric(18,2), content_hash bytea, pdf_document_id uuid, unique (quote_id, revision_no));
create table quote_line (id uuid primary key, revision_id uuid references quote_revision(id), work_item_id uuid references work_item(id), ord int,
  description_override text, quantity numeric(12,3), unit_price numeric(18,2), line_discount_percent numeric(5,2) default 0, billable bool default true,
  line_total numeric(18,2));
create table milestone (id uuid primary key, revision_id uuid references quote_revision(id), ord int, label text, percent numeric(5,2), amount numeric(18,2),
  trigger text not null, trigger_ref jsonb);
create table acceptance (id uuid primary key, revision_id uuid unique references quote_revision(id), method text not null, contact_id uuid, accepted_at timestamptz,
  evidence jsonb not null, revision_hash bytea not null);
create table order_ (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, number text, acceptance_id uuid references acceptance(id),
  project_id uuid, account_id uuid, currency char(3), amends_order_id uuid, state_id uuid);
create table order_line (id uuid primary key, order_id uuid references order_(id), work_item_id uuid references work_item(id), service_id uuid,
  description text, quantity numeric(12,3), unit_price numeric(18,2), billable bool default true, line_total numeric(18,2),
  status text not null default 'OPEN', superseded_by_line_id uuid);
create table milestone_instance (id uuid primary key, order_id uuid references order_(id), milestone_id uuid, amount numeric(18,2), trigger text, state text not null,
  triggered_at timestamptz, invoice_id uuid);

create table expected_intake (id uuid primary key, tenant_id uuid not null, order_id uuid, work_item_id uuid references work_item(id), test_definition_id uuid,
  specimen_type_id uuid, qty_expected numeric(12,3), ages int[], qty_received numeric(12,3) default 0);
create table intake (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, number text, project_id uuid references project(id), received_at timestamptz,
  delivered_by text, delivered_phone text, received_by uuid, intake_fields jsonb default '{}', state_id uuid);
create table specimen (id uuid primary key, tenant_id uuid not null, intake_id uuid references intake(id), work_item_id uuid, specimen_type_id uuid, position int,
  label_token text unique not null, planned_age int, current_stage text, current_location_id uuid, status text default 'OK');
create table sample (id uuid primary key, tenant_id uuid not null, intake_id uuid references intake(id), work_item_ids uuid[], name text, nature_id uuid,
  materials jsonb default '[]', label_token text unique not null, current_stage text, current_location_id uuid);
create table test_run (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, department_id uuid, number text, test_definition_id uuid,
  definition_version int, work_item_id uuid, intake_id uuid, specimen_ids uuid[], sample_id uuid, due_date date, age int, assigned_user_id uuid,
  equipment_id uuid, state_id uuid, measured_at timestamptz, reviewed_by uuid, reviewed_at timestamptz);
create index idx_test_run_due on test_run (tenant_id, branch_id, department_id, due_date) where state_id is not null;
create table measurement (id uuid primary key, test_run_id uuid references test_run(id), level text, subject_id text, key text, value_num numeric, value_text text,
  unit text, recorded_by uuid, recorded_at timestamptz, device_time timestamptz, client_op_id uuid unique, batch_id uuid);
create table computed_value (id uuid primary key, test_run_id uuid references test_run(id), level text, subject_id text, key text, value numeric, unit text,
  formula_version int, excluded bool default false, exclusion_reason text, overridden bool default false, override_reason text, original_value numeric,
  overridden_by uuid, overridden_at timestamptz, unique (test_run_id, level, subject_id, key));
create table report (id uuid primary key, tenant_id uuid not null, number text, project_id uuid, test_run_ids uuid[] not null, version int default 1,
  supersedes_report_id uuid, state_id uuid, issued_document_id uuid, reason text);

create table issued_document (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, kind text not null, number text not null,
  subject jsonb, digest jsonb, issued_at timestamptz not null, issued_by uuid, signatory_id uuid, template_version int, content_hash bytea,
  pdf_object_key text, pdf_sha256 bytea, status text not null default 'CURRENT', superseded_by_id uuid, revoked_reason text,
  verify_token text unique not null, short_code text not null, transparency_leaf_index bigint);
create table rendition (id uuid primary key, issued_document_id uuid references issued_document(id), options jsonb, produced_by uuid, produced_at timestamptz,
  object_key text, sha256 bytea);

create table invoice (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, number text, account_id uuid, project_id uuid, order_id uuid,
  source text, subtotal numeric(18,2), tax numeric(18,2), total numeric(18,2), currency char(3), due_date date,
  treasury_account_id uuid, state_id uuid, issued_document_id uuid, issued_at timestamptz);
create table invoice_line (id uuid primary key, invoice_id uuid references invoice(id), ord int, description text, quantity numeric(12,3),
  unit_price numeric(18,2), tax_rate numeric(5,2), line_total numeric(18,2), work_item_id uuid, milestone_instance_id uuid, order_line_id uuid);
create table credit_note (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, number text, invoice_id uuid references invoice(id),
  reason_id uuid, lines jsonb not null, total numeric(18,2), issued_document_id uuid, issued_at timestamptz);
create table payment (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, number text, account_id uuid, amount numeric(18,2), currency char(3),
  method_id uuid, paid_at date, reference text, proof_attachment_id uuid, recorded_by uuid, treasury_account_id uuid, provider_intent_id uuid, state text default 'RECORDED');
create table payment_allocation (payment_id uuid references payment(id), invoice_id uuid references invoice(id), amount numeric(18,2), primary key (payment_id, invoice_id));
create table treasury_entry (id uuid primary key, tenant_id uuid not null, treasury_account_id uuid, direction text, amount numeric(18,2), at timestamptz,
  origin_type text, origin_id uuid, label text, counter_entry_id uuid);

create table audit_event (id uuid primary key, tenant_id uuid not null, branch_id uuid, aggregate_type text, aggregate_id uuid, action text, actor_id uuid,
  actor_type text, at timestamptz default now(), before jsonb, after jsonb, context jsonb);
revoke update, delete on audit_event from app_role;

create table attachment (id uuid primary key, tenant_id uuid not null, owner_type text, owner_id uuid, kind text, object_key text, sha256 bytea, size bigint,
  mime text, uploaded_by uuid, uploaded_at timestamptz default now(), scanned bool default false);
create index idx_attachment_owner on attachment (owner_type, owner_id);
create table comment (id uuid primary key, tenant_id uuid not null, owner_type text, owner_id uuid, author_id uuid, body text, mentions uuid[], at timestamptz default now());
create table client_request (id uuid primary key, tenant_id uuid not null, branch_id uuid, account_id uuid, contact_id uuid, project_id uuid, type text, body text,
  state text default 'OPEN', converted_type text, converted_id uuid);
create table stock_location (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, site text, name text);
create table stock_movement (id uuid primary key, tenant_id uuid not null, item_type text, item_id uuid, from_location_id uuid, to_location_id uuid,
  qty numeric(12,3) not null, reason text not null, ref_type text, ref_id uuid, by_user uuid, at timestamptz default now());
create view stock_level as
  select tenant_id, item_type, item_id, location_id,
         sum(qty) as qty_total
  from (select tenant_id, item_type, item_id, to_location_id as location_id, qty from stock_movement where to_location_id is not null
        union all
        select tenant_id, item_type, item_id, from_location_id, -qty from stock_movement where from_location_id is not null) m
  group by 1,2,3,4;
create table stock_reservation (id uuid primary key, tenant_id uuid not null, item_type text, item_id uuid, location_id uuid, qty numeric(12,3), order_line_id uuid, released bool default false);
create table rental (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, number text, order_id uuid, lines jsonb not null, start_at timestamptz,
  due_back_at timestamptz, returned_at timestamptz, state_id uuid, penalty_amount numeric(18,2), condition_on_return jsonb);
create table work_order (id uuid primary key, tenant_id uuid not null, branch_id uuid not null, department_id uuid, number text, work_item_id uuid, project_id uuid,
  type text, planned_start date, deadline_optimal date, deadline_max date, state_id uuid, visit jsonb);
create table phase (id uuid primary key, work_order_id uuid references work_order(id), code text, ord int, weight numeric(5,2), state text default 'PENDING',
  requires_deliverable bool default false, started_at timestamptz, completed_at timestamptz);
create table phase_assignment (phase_id uuid references phase(id), responsible_id uuid, is_principal bool, weight_percent numeric(5,2), primary key (phase_id, responsible_id));
create table notification_delivery (id uuid primary key, tenant_id uuid not null, rule_id uuid, event_id uuid, recipient text, channel text, rendered jsonb,
  status text, attempts int default 0, last_error text, sent_at timestamptz);
create table fx_rate (tenant_id uuid, from_ccy char(3), to_ccy char(3), valid_from date, rate numeric(18,8), primary key (tenant_id, from_ccy, to_ccy, valid_from));
create view test_run_with_semantic as
  select r.*, ws.semantic as state_semantic from test_run r join workflow_state ws on ws.id = r.state_id;
-- procrastinate_jobs tables are created by Procrastinate's schema; outbox = procrastinate job with queueing_lock = event_id||handler
```

## Appendix C — State machines (default templates)

### C.1 TEST_RUN
| From | To | Action | Guards | Effects |
|---|---|---|---|---|
| SCHEDULED | IN_PROGRESS | test_run.edit (start) | assigned or actor has assign | — |
| IN_PROGRESS | MEASURED | test_run.edit (measure) | all_measurements_present, no_rule_blocking | notify(supervisor_measured) |
| MEASURED | UNDER_REVIEW | review_results | actor_is_not_entrant (if branch setting) | — |
| UNDER_REVIEW | VALIDATED | review_results | — | — |
| UNDER_REVIEW | IN_PROGRESS | review_results (return) | reason | notify(technician_returned) |
| VALIDATED | REPORTED | (system on report.issued) | — | increment_delivered, close_parent_if_complete |
| any non-terminal | CANCELLED | test_run.cancel | reason | release specimens |

### C.2 REPORT
| From | To | Action | Guards | Effects |
|---|---|---|---|---|
| DRAFT | ISSUED | report.issue (+ report.sign if signature required) | all runs VALIDATED, signatory_authorised | allocate_number, issue_document, notify(client_report_issued), make_milestone_invoiceable(ON_REPORT) |
| ISSUED | SUPERSEDED | (system on new version issued) | — | document status update, notify(client_report_superseded) |
| ISSUED | REVOKED | report.cancel | reason | document status update, notify(client_report_revoked), decrement_delivered |

### C.3 INVOICE
| From | To | Action | Guards | Effects |
|---|---|---|---|---|
| DRAFT | ISSUED | invoice.issue | invoice_has_lines | allocate_number (gap-free), issue_document, notify(client_invoice_issued), milestone instances → INVOICED, qty_invoiced update |
| DRAFT | CANCELLED | invoice.cancel | — | — |
| ISSUED | (paid states derived) | — | — | — |

### C.4 RENTAL
| From | To | Action | Guards | Effects |
|---|---|---|---|---|
| RESERVED | ACTIVE | rental.edit (hand over) | stock_available | stock movement RENTAL_OUT, issue_document(RENTAL_NOTE) |
| ACTIVE | LATE | (system daily) | today > due_back | notify(rental_late) |
| ACTIVE/LATE | RETURNED | rental.edit (return) | condition recorded | stock movement RENTAL_IN, compute penalty → penalty work item + milestone |
| RETURNED | CLOSED | rental.edit | penalties invoiced or waived | — |
| RESERVED | CANCELLED | rental.cancel | reason | release_stock |

### C.5 TRANSFER
DRAFT → VALIDATED (transfer.approve; stock_available) → IN_TRANSIT (dispatch; movements OUT)
→ RECEIVED (receive with quantities; movements IN; remainder stays IN_TRANSIT) ; DRAFT/VALIDATED → CANCELLED.

### C.6 WORK_ORDER / PHASE
PLANNED → IN_PROGRESS (first phase started) → LATE (system, deadline_max passed) → COMPLETED
(all phases COMPLETED; effects: item DELIVERED, make_milestone_invoiceable(ON_DELIVERY)) ;
any → CANCELLED (reason). PHASE: PENDING → IN_PROGRESS → COMPLETED (assignment principal or supervisor).

### C.7 INTAKE / PROJECT / ACCOUNT
INTAKE: REGISTERED → PARTIALLY_PROCESSED (some runs reported) → PROCESSED (all reported) ; → CANCELLED (no measurements yet).
PROJECT: OPEN ↔ ON_HOLD ; OPEN → CLOSED (all items delivered & paid or cancelled) ; → CANCELLED.
ACCOUNT: ACTIVE ↔ INACTIVE ; ACTIVE → BLOCKED (finance, reason; blocks new quotes) → ACTIVE.

## Appendix D — Document layouts (default templates)

### D.1 Common frame
Header: tenant/branch logo (left), legal name, address, phones, e-mail, registration numbers
(right); document title, number, date, page x/y. Footer: QR (left) + short code + "Verify at
verify.<domain>", branch bank account and tax id where relevant, template version.

### D.2 Quote
1. Addressee block: account legal name, contact, project title and location, reference
   documents, quote number, revision number, date, validity.
2. Object paragraph (from template variable, editable per quote).
3. Lines table grouped by task headings: # · Designation · Unit · Qty · Unit price · Total
   (PM lines show "PM" instead of amounts).
4. Totals block: subtotal, discount (label with % or amount), taxable, VAT (rate), total; in
   words (locale-aware).
5. Payment schedule table: milestone label · % · amount · trigger description.
6. Conditions of the offer (bulleted from vocabulary), client note.
7. Signatures: "Le Client (bon pour accord)" box · signatory of the branch (image per print
   options) · QR.

### D.3 Concrete crushing report (PV)
1. Title "Procès-verbal d'écrasement d'éprouvettes de béton", number, date, report version.
2. Identification table: account, project, site, structure part, sampling by (LAB/CLIENT),
   intake number and date, fabrication date, test date, age, slump, placement.
3. Mix design table: constituent · name · dosage (kg/m³ or l/m³).
4. Results table: Ref · Type/Dim · Age (d) · Weight (kg) · Load (kgf) · Stress (kg/cm²) ·
   Stress (MPa) · Mean (MPa); excluded specimens marked with a note; overrides footnoted.
5. Remarks (nota), operator, instrument, reviewer.
6. Signature block, QR.

### D.4 Invoice
Addressee (legal name, tax id, address), invoice number (gap-free), date, due date, project
and order references; lines (description, qty, unit price, VAT rate, total); totals (subtotal,
VAT, total, amount in words); payment terms; bank account(s) printed; legal mentions; QR.

### D.5 Labels
50 × 30 mm (configurable): QR (token), intake number, position, project short title, planned
age/test date, specimen type; high-contrast, thermal-printer ZPL and PDF sheet variants.

## Appendix E — Seed data for a new tenant

- **Departments**: Commercial, Finance, Concrete, Soils & Aggregates, Geotechnics, Assets.
- **Vocabularies**: participant roles (MO, MOE, BCT, Contractor, Subcontractor); contact
  functions (Director, Site manager, Engineer, Accountant, Purchaser); priorities (Low,
  Normal, High, Urgent); sample natures (Soil, Aggregate, Sand, Bitumen, Asphalt mix, Steel,
  Cement, Concrete, Block); curing locations (Concrete tank, CBR tank, Shelf A…); payment
  methods (Cash, Bank transfer, Cheque, Mobile money); reasons (Client request, Error,
  Duplicate, Other); block types (Hollow, Solid, Hourdis); specimen shapes (Cylinder, Cube,
  Prism); quote conditions (Validity 30 days, Prices excl. VAT, Payment terms, Samples
  supplied by client, Reports issued after payment).
- **Numbering** (branch default): ACCOUNT `CL-{SEQ:5}`; PROJECT `AF-{YYYY}-{SEQ:4}`; QUOTE
  `DV-{BRANCH}-{YYYY}-{SEQ:4}`; ORDER `CM-{YYYY}-{SEQ:4}`; CONTRACT `CT-{YYYY}-{SEQ:3}`;
  INTAKE `RC-{YY}-{SEQ:4}`; TEST_RUN `ES-{YY}-{SEQ:5}`; REPORT `PV-{BRANCH}-{YYYY}-{SEQ:4}`;
  INVOICE `FA-{YYYY}-{SEQ:5}` (gap-free); CREDIT_NOTE `AV-{YYYY}-{SEQ:4}` (gap-free); PAYMENT
  `PA-{YYYY}-{SEQ:5}`; RENTAL `LO-{YY}-{SEQ:4}`; TRANSFER `TR-{YY}-{SEQ:4}`; WORK_ORDER `OT-{YY}-{SEQ:4}`.
- **Workflows**: one default per kind with the semantics of §10.3 and the transitions of
  §13.3 and Appendix C.
- **Roles**: the templates of §9.3.
- **Test definitions**: the four of §14.6 (ACTIVE) plus the list of §14.7 as DRAFT stubs.
- **Templates**: quote, contract, PV concrete, PV blocks, sieve report, water-content report,
  generic test report, invoice, credit note, receipt, statement, rental/sale/outing/transfer
  notes, labels, daily digest; FR and EN.
- **Notification rules**: the defaults of §19.3.
- **Print profiles**: signature image on, digital signature off (portal forces on), QR on.

## Appendix F — Tablet flows

### F.1 Intake (stepper)
1. **Project**: search by number/title/account or scan a quote QR; show account, open
   orders, outstanding expected intakes (item, type, remaining qty, ages).
2. **What arrived**: for each expected line: enter received qty (default remaining); add
   unexpected line (variance) with service search; for SPECIMEN tests: distribution table by
   age with running total = received qty (validation blocks Next); for SAMPLE tests: sample
   name, nature, materials.
3. **Intake fields**: union of definitions' fields (fabrication date required for age
   scheduling; mix design structured; slump; sampling by; site; structure part).
4. **Handover**: delivered by (name, phone; autocomplete from account contacts), photos of
   specimens/delivery note, remarks.
5. **Confirm**: summary; `Save` → runs scheduled → labels sent to printer; `Print again`;
   `New intake same project`.
Validations: Σ ages = qty; ages allowed; fabrication date ≤ today; duplicates warned.

### F.2 Worksheet
1. Scan any specimen label (or pick a run from "My day"); the run and its sibling specimens
   load; header shows project, intake, age, due date, definition and version.
2. Inputs per specimen in a grid (weight, load); numeric keypad; unit hints; range
   validation inline; computed stress and MPa update on blur; aggregates panel shows mean,
   excluded specimens and rule messages.
3. Specimen actions: `Missing`, `Damaged` (reason), `Swap position` (scan).
4. Instrument: pick from equipment register (defaults to last used; warns if maintenance due).
5. Photos and remarks. `Save` (works offline, badge shows pending sync). `Mark measured`
   (server re-validates; BLOCK returns the reason).
6. Supervisor path: `Review` → `Validate` / `Return` → `Issue report` (print options dialog).

## Appendix G — Payload examples

### G.1 Create revision lines
```json
PUT /v1/quotes/6f1…/revisions/2/lines
{ "lines": [
  {"work_item_id":"a1…","quantity":12,"unit_price":"2500.00","line_discount_percent":0,"billable":true},
  {"work_item_id":"a2…","quantity":4,"unit_price":"2500.00","billable":true},
  {"work_item_id":"a3…","quantity":1,"unit_price":"0.00","billable":false,"description_override":"Prélèvement sur site (PM)"} ] }
→ 200 { "subtotal":"40000.00","discount_amount":"0.00","taxable":"40000.00","tax_amount":"6400.00","total":"46400.00" }
```
### G.2 Portal acceptance
```json
POST /v1/portal/quotes/6f1…:request-otp → 202 { "challenge_id":"c9…", "channel":"SMS", "expires_in":600 }
POST /v1/portal/quotes/6f1…:accept { "challenge_id":"c9…", "otp":"482913", "terms_version":"2026-01" }
→ 201 { "acceptance_id":"…", "order_number":"CM-2026-0087", "revision_hash":"…" }
```
### G.3 Intake
```json
POST /v1/intakes
{ "project_id":"p1…", "received_at":"2026-09-11T09:20:00Z", "delivered_by":"A. Sow", "delivered_phone":"+22246…",
  "lines":[ {"expected_intake_id":"e1…","specimen_type_id":"CYL_16x32","qty":12,"ages":[{"age":7,"qty":4},{"age":28,"qty":8}]} ],
  "intake_fields":{"fabrication_date":"2026-09-10","sampling_by":"LAB","slump_cm":8,"structure_part":"Semelles S1-S4",
    "mix_design":{"cement":{"name":"CEM II 42.5","dosage":350},"water":{"name":"Eau","dosage":175}} } }
→ 201 { "id":"i1…","number":"RC-26-0412","specimens":12,"test_runs":[{"number":"ES-26-01890","due_date":"2026-09-17","age":7},{"number":"ES-26-01891","due_date":"2026-10-08","age":28}],
        "labels_job_id":"j…" }
```
### G.4 Offline measurement sync
```json
POST /v1/sync/measurements
{ "batch_id":"b7…", "device_id":"tab-03", "ops":[
  {"client_op_id":"o1…","test_run_id":"r1…","level":"PER_SPECIMEN","subject_id":"3","key":"weight_kg","value_num":12.41,"device_time":"2026-09-17T08:03:11Z"},
  {"client_op_id":"o2…","test_run_id":"r1…","level":"PER_SPECIMEN","subject_id":"3","key":"load_kgf","value_num":45210,"device_time":"2026-09-17T08:03:40Z"},
  {"client_op_id":"o3…","type":"transition","test_run_id":"r1…","to":"MEASURED"} ] }
→ 200 { "applied":["o1…","o2…"], "rejected":[{"op":"o3…","code":"RULE_BLOCK","message_key":"lab.rule.blocked","params":{"rule":"SERIES_MONOTONIC"}}] }
```
### G.5 Verify
```json
GET /v1/verify/7K2MQ9X3…
→ 200 { "issuer":"Mizan Labs / Nouakchott", "kind":"REPORT", "number":"PV-NKC-2026-0412", "issued_at":"2026-10-09",
        "account":"SOGECO", "project":"AF-2026-0031 — Immeuble R+4 Tevragh Zeina", "status":"SUPERSEDED", "superseded_by":"PV-NKC-2026-0419" }
POST /v1/verify/7K2MQ9X3…/digest { "short_code":"H7Q4-2K" } → 200 { "n":6, "age":28, "mean":"22.4", "unit":"MPa", "excluded":1 }
```

## Appendix H — Runbooks

| Runbook | Steps |
|---|---|
| Deploy | merge to main → pipeline builds → staging auto-deploys → approve production → migrations job → new revision at 10 % traffic → automated checks → 100 % |
| Rollback | shift 100 % traffic to the previous Cloud Run revision (seconds); migrations are backward compatible, no DB rollback needed; a reverting migration ships in the next release |
| Restore | Cloud SQL PITR clone to a point in time (or logical dump from R2) into staging → integrity checks (counts, hashes of issued documents) → promote by switching `DATABASE_URL` secret or discard; record evidence |
| Rotate signing key | create new key in KMS → publish public key (overlap) → switch branch signer → keep old key for verification 10 years |
| Add tenant | platform console → New tenant → tenant admin invited → setup wizard |
| Add branch | admin console → New branch (wizard) or clone configuration from existing branch → numbering, signatories, treasury accounts |
| Add a test | admin console → Catalog → New definition → inputs/computed/rules → sandbox with sample data → activate → create service + price → menu appears |
| Change a status name | admin console → Workflows → edit label (semantic unchanged); no deploy |
| Incident: failed notifications | health page → delivery log → provider status → retry batch |
| Incident: verification spike | fraud queue → inspect attempts → revoke if a genuine document leaked with altered copies → notify account |

## Appendix I — Risks and mitigations

| Risk | Mitigation |
|---|---|
| Test-definition engine too rigid for a future test | Inputs at four levels, structured intake fields, rule effects, versioning; escape hatch: custom computed key implemented in Go behind the same interface |
| PAdES-LTA or PDF/A conformance regressions | veraPDF and an independent PAdES validator run in CI on golden documents; pyHanko pinned and upgraded deliberately |
| Offline conflicts on shared runs | Runs assigned to one technician by default; conflicts surfaced, both values audited |
| Tenant leakage through a missed predicate | RLS is the backstop; authz fuzz tests per endpoint × role |
| Numbering gaps on invoices | ON_ISSUE allocation inside the issuing transaction; gap report in Finance |
| Notification provider outages | Retries, fallback channel order (WhatsApp → SMS → e-mail), delivery log alerts |
| Cloud region or provider incident | Managed HA database with PITR, nightly cross-provider logical dump to R2, Terraform to recreate the stack in another region in < 1 h; static apps already global on Cloudflare |
| Key compromise | KMS custody, separate signing identity, rotation runbook, transparency log for forensics |
| Scope creep | Phased plan with acceptance criteria; configuration absorbs variation instead of code |

## Appendix J — Canonical test definition (JSON)

```json
{
  "code": "CONCRETE_COMPRESSION",
  "version": 1,
  "labels": { "fr": "Écrasement d'éprouvettes béton", "en": "Concrete compressive strength" },
  "category": "TESTS.CONCRETE",
  "department": "CONCRETE",
  "method_ref": "NF EN 12390-3",
  "unit_under_test": "SPECIMEN",
  "specimen_types": ["CYL_16x32", "CYL_15x30", "CUBE_15"],
  "scheduling": { "type": "AGE", "reference_field": "fabrication_date", "allowed_ages": [2, 3, 7, 14, 28, 56, 90] },
  "stages": [
    { "code": "RECEIVED", "labels": { "fr": "Reçu", "en": "Received" } },
    { "code": "CURING", "labels": { "fr": "En cure", "en": "Curing" }, "location_vocab": "curing_location" },
    { "code": "TESTING", "labels": { "fr": "En essai", "en": "Testing" } },
    { "code": "REPORTED", "labels": { "fr": "Rapporté", "en": "Reported" }, "is_terminal": true }
  ],
  "intake_fields": [
    { "key": "fabrication_date", "type": "date", "required": true, "labels": { "fr": "Date de fabrication", "en": "Fabrication date" } },
    { "key": "sampling_by", "type": "enum", "options": ["LAB", "CLIENT"], "required": true, "labels": { "fr": "Prélèvement", "en": "Sampled by" } },
    { "key": "structure_part", "type": "text", "labels": { "fr": "Partie d'ouvrage", "en": "Structure part" } },
    { "key": "site", "type": "text", "labels": { "fr": "Chantier", "en": "Site" } },
    { "key": "slump_cm", "type": "number", "unit": "cm", "min": 0, "max": 30 },
    { "key": "placement", "type": "text" },
    { "key": "mix_design", "type": "structured", "schema": {
        "gravel1": { "name": "text", "dosage": "number:kg/m3" }, "gravel2": { "name": "text", "dosage": "number:kg/m3" },
        "sand1": { "name": "text", "dosage": "number:kg/m3" }, "sand2": { "name": "text", "dosage": "number:kg/m3" },
        "cement": { "name": "text", "dosage": "number:kg/m3" }, "admixture": { "name": "text", "dosage": "number:l/m3" },
        "water": { "name": "text", "dosage": "number:l/m3" } } }
  ],
  "inputs": [
    { "key": "weight_kg", "type": "number", "unit": "kg", "level": "PER_SPECIMEN", "required": true, "min": 0, "max": 50, "step": 0.01 },
    { "key": "load_kgf", "type": "number", "unit": "kgf", "level": "PER_SPECIMEN", "required": true, "min": 0, "max": 200000, "step": 1 }
  ],
  "computed": [
    { "key": "section_cm2", "unit": "cm2", "level": "PER_SPECIMEN", "precision": 2,
      "formula": "specimen.shape == 'CYLINDER' ? pi() * specimen.d ^ 2 / 4 : specimen.side ^ 2" },
    { "key": "stress_kgcm2", "unit": "kgf/cm2", "level": "PER_SPECIMEN", "precision": 0, "formula": "round(inputs.load_kgf / computed.section_cm2, 0)" },
    { "key": "stress_mpa", "unit": "MPa", "level": "PER_SPECIMEN", "precision": 1, "formula": "round(computed.stress_kgcm2 / 10, 1)" }
  ],
  "aggregates": [
    { "key": "mean_mpa", "unit": "MPa", "precision": 1, "formula": "round(avg(specimens.stress_mpa), 1)" },
    { "key": "n_tested", "formula": "count(specimens.stress_mpa)" }
  ],
  "rules": [
    { "code": "SINGLE_OUTLIER", "effect": "EXCLUDE_AND_RECOMPUTE", "params": { "threshold": 5 },
      "expression": "count(filter(specimens, {aggregates.mean_mpa - .stress_mpa >= params.threshold})) == 1",
      "target": "argmin(specimens.stress_mpa)",
      "labels": { "fr": "Une éprouvette écartée (écart ≥ {threshold} MPa)", "en": "One specimen excluded (deviation ≥ {threshold} MPa)" } },
    { "code": "MULTI_OUTLIER", "effect": "FLAG", "params": { "threshold": 5 },
      "expression": "count(filter(specimens, {aggregates.mean_mpa - .stress_mpa >= params.threshold})) >= 2",
      "labels": { "fr": "Dispersion élevée : vérifier", "en": "High dispersion: check" } }
  ],
  "required_equipment_class": "COMPRESSION_PRESS",
  "report_template": "PV_CONCRETE",
  "report_columns": ["ref", "specimen_type", "age", "weight_kg", "load_kgf", "stress_kgcm2", "stress_mpa", "mean_mpa"],
  "unit_of_sale": "PER_SPECIMEN"
}
```

## Appendix K — Formula language

### K.1 Grammar (EBNF)
```
expr        := ternary ;
ternary     := or_expr [ "?" expr ":" expr ] ;
or_expr     := and_expr { "or" and_expr } ;
and_expr    := not_expr { "and" not_expr } ;
not_expr    := [ "not" ] comparison ;
comparison  := additive { ( "==" | "!=" | "<" | "<=" | ">" | ">=" ) additive } ;
additive    := term { ( "+" | "-" ) term } ;
term        := power { ( "*" | "/" | "%" ) power } ;
power       := unary [ "^" power ] ;
unary       := [ "-" ] primary ;
primary     := number | string | ident { "." ident | "[" expr "]" } | call | "(" expr ")" | lambda ;
call        := ident "(" [ expr { "," expr } ] ")" ;
lambda      := "{" expr "}"          (* body may use "." for the current element *)
```
### K.2 Namespaces
`inputs.<key>` (current subject), `computed.<key>` (current subject, already evaluated
keys), `specimen.<prop>` (type properties: shape, d, side, L, W, H, gross_area, net_factor),
`run.<field>` (per-run inputs), `intake.<field>` (intake fields), `series[i].<key>`,
`portions[i].<key>`, `specimens.<key>` (vector over non-excluded subjects), `aggregates.<key>`,
`params.<name>` (rule parameters), `const.<name>` (branch constants).
### K.3 Functions
`round(x, n)`, `floor`, `ceil`, `abs`, `sqrt`, `pow`, `pi()`, `min(a,b|vec)`, `max`, `avg(vec)`,
`sum(vec)`, `count(vec)`, `stddev(vec)`, `median(vec)`, `filter(vec, {pred})`, `map(vec, {f})`,
`argmin(vec)`, `argmax(vec)`, `first`, `last`, `is_monotonic_nondecreasing(vec)`, `to(x, "unit")`,
`days_between(d1, d2)`, `coalesce(a, b)`.
### K.4 Evaluation rules
Order: computed keys in declaration order per subject → aggregates → rules in order; rules
with `EXCLUDE_AND_RECOMPUTE` mark `target` excluded and trigger one recompute of aggregates
(no cascading beyond one pass unless `params.iterative=true`, max 3). Division by zero and
missing required inputs yield `BLOCK` with a message key. Execution limit 50 ms per run;
expressions compiled and cached per definition version.

## Appendix L — Read models (SQL)

```sql
-- invoice paid status
create view invoice_paid_status as
select i.id, i.total, coalesce(sum(pa.amount),0) - coalesce((select sum(cn.total) from credit_note cn where cn.invoice_id = i.id),0) as paid,
  case when coalesce(sum(pa.amount),0) = 0 then case when i.due_date < current_date then 'OVERDUE' else 'UNPAID' end
       when coalesce(sum(pa.amount),0) < i.total then 'PARTIALLY_PAID' else 'PAID' end as paid_status
from invoice i left join payment_allocation pa on pa.invoice_id = i.id
where i.issued_at is not null group by i.id;

-- work_item_state (materialised view refreshed by events; fallback every 5 min)
create materialized view work_item_state as
with commercial as (
  select ql.work_item_id,
         min(case ws.semantic when 'ACCEPTED' then 0 when 'NEGOTIATING' then 1 when 'SENT' then 2 when 'PENDING_APPROVAL' then 3
                              when 'SUSPENDED' then 4 when 'DRAFT' then 5 when 'REFUSED' then 6 when 'EXPIRED' then 7 else 8 end) as rank
  from quote_line ql join quote_revision qr on qr.id = ql.revision_id join quote q on q.id = qr.quote_id
  join workflow_state ws on ws.id = q.state_id group by ql.work_item_id),
invoiced as (
  select il.work_item_id, sum(il.line_total) as invoiced,
         sum(il.line_total * coalesce(p.paid_ratio, 0)) as paid
  from invoice_line il join invoice i on i.id = il.invoice_id
  left join (select ips.id, least(ips.paid / nullif(ips.total,0), 1) as paid_ratio from invoice_paid_status ips) p on p.id = i.id
  where il.work_item_id is not null and i.issued_at is not null group by il.work_item_id),
milestone_share as (
  -- milestone invoices are attributed pro rata to the order's items by line_total
  select ol.work_item_id,
         sum(il.line_total * ol.line_total / nullif(ot.order_total,0)) as invoiced,
         sum(il.line_total * ol.line_total / nullif(ot.order_total,0) * coalesce(p.paid_ratio,0)) as paid,
         bool_or(mi.state = 'INVOICEABLE') as invoiceable
  from order_line ol
  join (select order_id, sum(line_total) as order_total from order_line where billable group by order_id) ot on ot.order_id = ol.order_id
  left join milestone_instance mi on mi.order_id = ol.order_id
  left join invoice_line il on il.milestone_instance_id = mi.id
  left join invoice i on i.id = il.invoice_id and i.issued_at is not null
  left join (select ips.id, least(ips.paid / nullif(ips.total,0), 1) as paid_ratio from invoice_paid_status ips) p on p.id = i.id
  where ol.billable group by ol.work_item_id)
select wi.id as work_item_id, wi.project_id,
  case c.rank when 0 then 'ACCEPTED' when 1 then 'NEGOTIATING' when 2 then 'SENT' when 3 then 'PENDING_APPROVAL' when 4 then 'SUSPENDED'
              when 5 then 'DRAFT' when 6 then 'REFUSED' when 7 then 'EXPIRED' else 'NOT_QUOTED' end as commercial_state,
  case when wi.qty_reported >= greatest(wi.qty_expected, 0.001) then 'DELIVERED'
       when wi.qty_reported > 0 then 'PARTIALLY_DELIVERED'
       when wi.qty_received > 0 then 'IN_PROGRESS'
       when wi.qty_expected > 0 then 'AWAITING_SAMPLES' else 'NOT_STARTED' end as execution_state,
  case when coalesce(inv.invoiced,0) + coalesce(ms.invoiced,0) = 0
            then case when coalesce(ms.invoiceable,false) or wi.qty_reported > wi.qty_invoiced then 'INVOICEABLE' else 'NOT_INVOICEABLE' end
       when coalesce(inv.paid,0) + coalesce(ms.paid,0) = 0 then 'INVOICED'
       when coalesce(inv.paid,0) + coalesce(ms.paid,0) < coalesce(inv.invoiced,0) + coalesce(ms.invoiced,0) - 0.005 then 'PARTIALLY_PAID'
       else 'PAID' end as financial_state
from work_item wi
left join commercial c on c.work_item_id = wi.id
left join invoiced inv on inv.work_item_id = wi.id
left join milestone_share ms on ms.work_item_id = wi.id;
create unique index on work_item_state (work_item_id);

-- receivables ageing per account
create view receivables_ageing as
select i.tenant_id, i.branch_id, i.account_id,
  sum(case when current_date - i.due_date between 0 and 30 then i.total - s.paid else 0 end) as b0_30,
  sum(case when current_date - i.due_date between 31 and 60 then i.total - s.paid else 0 end) as b31_60,
  sum(case when current_date - i.due_date between 61 and 90 then i.total - s.paid else 0 end) as b61_90,
  sum(case when current_date - i.due_date > 90 then i.total - s.paid else 0 end) as b90_plus
from invoice i join invoice_paid_status s on s.id = i.id where s.paid_status <> 'PAID'
group by 1,2,3;

-- department daily load
create view department_daily_load as
select tenant_id, branch_id, department_id, due_date, count(*) as runs,
  count(*) filter (where state_semantic in ('SCHEDULED','IN_PROGRESS')) as open_runs
from test_run_with_semantic group by 1,2,3,4;
```

## Appendix M — Event handlers (procedures)

| Event | Handler (module) | Procedure |
|---|---|---|
| order.created | project.on_order_created | for each order line: `work_item.qty_expected += qty`; refresh `work_item_state` |
| order.created | lab.provision | for LAB_TEST lines: insert `expected_intake(qty_expected, specimen_type, ages from options)` |
| order.created | assets.reserve | for RENTAL/SALE lines: `stock_level.qty_reserved += qty` (atomic), insert reservation |
| order.created | delivery.provision | for STUDY/FIELD lines: create `work_order` with phases from template |
| order.created | sales.milestones | insert `milestone_instance` per milestone with computed amounts; ON_ACCEPTANCE → INVOICEABLE + event |
| intake.registered | lab.schedule | create test runs (§14.3); update `expected_intake.qty_received`, `work_item.qty_received`; emit test_run.scheduled |
| intake.registered | notify | rule intake_registered → client TECHNICAL contact |
| test_run.measured | notify | supervisor of department |
| report.issued | project | `work_item.qty_reported += units`; set `delivered_at` when complete; refresh state |
| report.issued | sales | milestone instances with trigger ON_REPORT and matching items → INVOICEABLE; emit milestone.invoiceable |
| report.issued | lab | runs → REPORTED; specimens stage → REPORTED |
| report.issued | notify | client contacts (e-mail with link, WhatsApp, SMS), portal inbox |
| work_item.delivered | sales | ON_DELIVERY milestones → INVOICEABLE |
| invoice.issued | project | `qty_invoiced` update (progress invoices); refresh financial state |
| invoice.issued | sales | milestone instances → INVOICED |
| payment.allocated | project/finance | refresh `invoice_paid_status`, `work_item_state`, `account_balance`; emit invoice.paid when covered |
| rental.returned | finance | if penalty > 0: create penalty work item (FEE) on project, milestone instance INVOICEABLE |
| stage.changed | lab | update `current_stage`, `current_location` on subject |
| test_run.overdue (daily) | notify | supervisor digest and technician reminder |
| verification.suspicious | notify | branch manager; open fraud case |
| config.changed | authz cache | invalidate cached grants for affected roles/users |

## Appendix N — Spreadsheet import specifications

All imports: XLSX/CSV with a downloadable template; first row headers; validation report per
row (`row, column, message_key`); preview before commit; commit is transactional per file.

| Import | Columns (required*) | Validations |
|---|---|---|
| Accounts | legal_name*, tax_id, legal_form, address, city, country, phone, email, tier_code, document_locale | duplicate on normalised name / tax_id → warning with merge choice |
| Contacts | account_number*, first_name*, last_name*, function_code, phone, whatsapp, email, roles (pipe-separated), portal (Y/N) | account must exist; e-mail format; roles in catalogue |
| Services | category_code*, code*, label_fr*, label_en, kind*, unit_of_sale*, department_code*, test_definition_code / phase_template_code / equipment_class_code | kind-specific link must exist |
| Prices | price_list_code*, service_code*, specimen_type_code, unit_price*, min_qty | numeric, currency of list |
| Equipment | class_code*, code*, serial, location_code*, condition_code, calibration_due | location exists |
| Stock counts | item_code*, location_code*, counted_qty* | creates ADJUSTMENT movements with reason "count" |
| Vocabularies | kind*, code*, label_fr*, label_en, colour, order | unique code per kind |
| Users | email*, display_name*, branch_code*, department_code, role_code* | role exists; invite sent |

## Appendix O — Route maps

**Back-office** (`/`): `/home`, `/search`, `/inbox`, `/projects`, `/projects/:id/(overview|work|quotes|intakes|tests|reports|finance|assets|delivery|documents|history)`,
`/commercial/(dashboard|accounts|accounts/:id|contacts|quotes|quotes/:id|quotes/:id/revisions/:n/edit|contracts|orders|requests)`,
`/lab/(dashboard|intake/new|intakes|calendar|runs|runs/:id/worksheet|stages|review|reports|tests|tests/:code|samples)`,
`/finance/(dashboard|to-invoice|invoices|invoices/:id|credit-notes|payments|treasury|statements|dunning|reconciliation)`,
`/assets/(dashboard|equipment|stock|consumables|rentals|sales|outings|transfers|maintenance|fleet|calendar|alerts)`,
`/delivery/(dashboard|work-orders|work-orders/:id|responsibles)`, `/settings/profile`.

**Admin console** (`/`): `/platform/(tenants|keys|health)`, `/org/(tenant|branches|branches/:id|departments|signatories|treasury-accounts)`,
`/access/(users|memberships|roles|roles/:id/matrix|view-as)`, `/numbering`, `/vocabularies/:kind`, `/workflows/:kind`,
`/catalog/(categories|services|test-definitions|test-definitions/:id|specimen-types|sieve-sets|phase-templates|equipment-classes)`,
`/pricing/(price-lists|tax-rules)`, `/documents/(templates|templates/:id|print-profiles)`, `/notifications/(rules|templates|providers|log)`,
`/portal`, `/integrations`, `/audit`, `/setup`.

**Client portal** (`/`): `/home`, `/projects`, `/projects/:id`, `/quotes`, `/quotes/:id`, `/reports`, `/invoices`, `/invoices/:id`,
`/payments`, `/requests`, `/requests/new`, `/account`, `/history`.

**Verification** (`/`): `/#<jws>` (QR), `/d/:token`, `/keys`, `/transparency`, `/offline`.

## Appendix P — Default message templates (FR / EN)

| Rule | Channel | FR | EN |
|---|---|---|---|
| quote_sent | e-mail subject | Devis {{quote.number}} rév. {{rev}} — {{project.title}} | Quote {{quote.number}} rev. {{rev}} — {{project.title}} |
| quote_sent | WhatsApp | Bonjour {{contact.first_name}}, votre devis {{quote.number}} ({{total}} {{currency}}) est disponible : {{portal_link}} | Hello {{contact.first_name}}, your quote {{quote.number}} ({{total}} {{currency}}) is available: {{portal_link}} |
| intake_registered | SMS | Mizan Labs : {{qty}} éprouvettes reçues pour {{project.title}} le {{date}}. Essais prévus : {{dates}}. | Mizan Labs: {{qty}} specimens received for {{project.title}} on {{date}}. Tests planned: {{dates}}. |
| report_issued | e-mail | Votre rapport {{report.number}} ({{test.label}}, {{age}} j) est émis. Télécharger : {{portal_link}}. Vérifier : {{verify_link}} | Your report {{report.number}} ({{test.label}}, {{age}} d) is issued. Download: {{portal_link}}. Verify: {{verify_link}} |
| invoice_issued | e-mail | Facture {{invoice.number}} de {{total}} {{currency}}, échéance {{due_date}}. | Invoice {{invoice.number}} for {{total}} {{currency}}, due {{due_date}}. |
| invoice_overdue | WhatsApp | Rappel : la facture {{invoice.number}} ({{balance}} {{currency}}) est échue depuis {{days}} jours. | Reminder: invoice {{invoice.number}} ({{balance}} {{currency}}) is {{days}} days overdue. |
| otp | SMS | Code Mizan Labs : {{otp}} (valable 10 min). Ne le partagez pas. | Mizan Labs code: {{otp}} (valid 10 min). Do not share it. |
| daily_digest | e-mail | Résumé du {{date}} — {{department}} : {{intakes}} réceptions, {{done}} essais faits, {{todo}} à faire, {{overdue}} en retard, {{tomorrow}} demain. | Digest {{date}} — {{department}}: {{intakes}} intakes, {{done}} runs done, {{todo}} to do, {{overdue}} overdue, {{tomorrow}} tomorrow. |

## Appendix Q — Deployment skeleton (Terraform + Cloud Run)

```hcl
# infra/terraform/cloud_run.tf (excerpt)
resource "google_cloud_run_v2_service" "api" {
  name = "lims-api"  location = var.region
  template {
    scaling { min_instance_count = 1  max_instance_count = 10 }
    containers {
      image = var.image
      args  = ["api"]
      resources { limits = { cpu = "1", memory = "1Gi" } }
      env { name = "DATABASE_URL"  value_source { secret_key_ref { secret = google_secret_manager_secret.db_url.id  version = "latest" } } }
      env { name = "R2_ENDPOINT"   value = var.r2_endpoint }
      env { name = "KMS_KEY_RING"  value = google_kms_key_ring.signing.id }
    }
    vpc_access { connector = google_vpc_access_connector.sql.id  egress = "PRIVATE_RANGES_ONLY" }
    max_instance_request_concurrency = 40
  }
  traffic { type = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"  percent = 100 }
}
resource "google_cloud_run_v2_service" "worker" {
  name = "lims-worker"  location = var.region
  template {
    scaling { min_instance_count = 1  max_instance_count = 5 }
    containers { image = var.image  args = ["worker"]  resources { limits = { cpu = "1", memory = "2Gi" }  cpu_idle = false } }
  }
}
resource "google_cloud_run_v2_job" "scheduler" { name = "lims-scheduler"  location = var.region
  template { template { containers { image = var.image  args = ["scheduler", "--once"] } } } }
resource "google_cloud_scheduler_job" "tick" { name = "lims-tick"  schedule = "*/5 * * * *"
  http_target { uri = "https://run.googleapis.com/v2/${google_cloud_run_v2_job.scheduler.id}:run"  http_method = "POST"
                oauth_token { service_account_email = google_service_account.scheduler.email } } }
resource "google_sql_database_instance" "pg" { name = "lims-pg"  database_version = "POSTGRES_16"  region = var.region
  settings { tier = "db-custom-2-8192"  availability_type = "REGIONAL"
             backup_configuration { enabled = true  point_in_time_recovery_enabled = true  transaction_log_retention_days = 7 }
             ip_configuration { ipv4_enabled = false  private_network = google_compute_network.vpc.id } } }
resource "google_kms_key_ring" "signing" { name = "lims-signing"  location = var.region }
resource "google_kms_crypto_key" "pdf_seal" { name = "branch-nkc-pdf"  key_ring = google_kms_key_ring.signing.id  purpose = "ASYMMETRIC_SIGN"
  version_template { algorithm = "RSA_SIGN_PKCS1_3072_SHA256"  protection_level = "HSM" } }
resource "google_kms_crypto_key" "qr" { name = "branch-nkc-qr"  key_ring = google_kms_key_ring.signing.id  purpose = "ASYMMETRIC_SIGN"
  version_template { algorithm = "EC_SIGN_ED25519"  protection_level = "SOFTWARE" } }
```
```
# Dockerfile (excerpt)
FROM python:3.12-slim AS build
RUN pip install uv && apt-get update && apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libcairo2 fonts-inter fonts-noto-core
COPY backend/ /app/  WORKDIR /app  RUN uv sync --frozen --no-dev
ENTRYPOINT ["/app/entrypoint.sh"]   # dispatches: api → granian config.asgi:application ; worker → procrastinate worker ; scheduler → periodic
```
Deploy flow (GitHub Actions): build → push → `terraform apply` (image variable) → migrations
job → new revision at 10 % traffic → checks → 100 %. Cloudflare: DNS records to Cloud Run
domain mappings; Pages projects per SPA with preview deployments per PR.

## Appendix R — Bootstrap: the first tasks in exact order

1. Repository skeleton: `uv init backend`, Django project `config`, `pnpm` workspace, Turborepo, `Makefile` (`dev`, `test`, `lint`, `build`, `migrate`, `seed`, `e2e`), `docker-compose.dev.yml` (PostgreSQL 16 with `unaccent`, `pg_trgm`, `citext`; MinIO; Mailpit).
2. Settings with `pydantic-settings`; ASGI app with Granian; health endpoints; Django Ninja API root with OpenAPI.
3. `platform/db`: tenant connection wrapper (`SET LOCAL app.tenant_id`), RLS migration helpers, test asserting every tenant model has a policy; base model mixin with common columns and `row_version`.
4. `apps/org`: tenant, branch, department, signatory, treasury account models + admin + API.
5. `apps/identity`: allauth setup (MFA, passkeys), JWT for SPAs, memberships, roles, grants; `platform/authz` (resolver, `Q` predicates, field-group serialisers); `/me`, `/me/permissions`; generated authz test matrix.
6. `apps/audit` + `platform/events`: audit model (immutable), outbox with Procrastinate, SSE endpoint (LISTEN/NOTIFY).
7. `apps/config`: numbering (atomic counter, patterns, preview, concurrency test), vocabularies, workflow engine (semantics, guards, effects registry, simulator), payment terms templates, signatories modes, branch settings.
8. `apps/documents`: template store, WeasyPrint renderer (PDF/A-3b), pyHanko sealing with KMS signer (dev: local key), issued documents, QR JWS, verification endpoints, transparency log; golden tests; veraPDF and PAdES validation in CI.
9. `apps/notify`: rules, e-mail channel, delivery log, in-app inbox.
10. Front-end packages: tokens (default theme + tenant primary), UI components, Storybook with axe; generated API client.
11. Admin console app: shell, organisation, users/roles/matrix, numbering, vocabularies, workflows, payment terms, signatories, templates, notification rules, setup wizard.
12. Back-office shell, home, project page skeleton, global search, command palette; portal and verify shells.
13. Terraform: project, Cloud Run api/worker/scheduler, Cloud SQL, KMS, Secret Manager, R2, Cloudflare DNS/Pages; GitHub Actions pipeline with canary traffic and rollback.
14. Seed command: demo tenant, branch, departments, roles, numbering, workflows, payment terms templates, signatory (IMAGE mode with placeholder), templates, four test definitions, notification rules.
15. Proceed with Phase 1 epics in order.

## Appendix S — Acceptance scenarios (golden paths)

```
Scenario: quote to accepted order
  Given an account "SOGECO" with a SIGNATORY contact and a project "AF-2026-0031"
  And services CONCRETE_COMPRESSION (per specimen, 2500) and FIELD_SAMPLING (per visit, 15000) priced in the branch list
  When commercial creates work items 12 × CONCRETE_COMPRESSION @28d, 4 × @7d, 1 × FIELD_SAMPLING
  And builds a quote from unquoted items with 5 % discount and milestones 30 % ON_ACCEPTANCE, 70 % ON_REPORT
  Then totals are subtotal 55000.00, discount 2750.00, taxable 52250.00, VAT 16 % 8360.00, total 60610.00
  And milestones are 18183.00 and 42427.00
  When the quote is sent
  Then revision 1 is frozen, a sealed PDF with QR exists, the client contact receives e-mail and WhatsApp
  When the client accepts in the portal with a valid OTP
  Then an order exists with 3 frozen lines, expected intakes 12 and 4 specimens, milestone 1 is INVOICEABLE
  And the work items' commercial state is ACCEPTED and financial state is INVOICEABLE

Scenario: intake to issued report, offline worksheet
  Given the accepted order above
  When reception registers 16 CYL_16x32 with ages {7: 4, 28: 12} and fabrication date D
  Then two test runs exist due D+7 and D+28, 16 labels are printed, the client receives an SMS
  When a technician, offline, records weights and loads for the 4 specimens of the 7-day run and marks measured
  And the tablet reconnects
  Then measurements are applied, stresses computed (section 201.06 cm²), mean rounded to 0.1 MPa
  And if one specimen is ≥ 5 MPa below the rounded mean it is excluded and the mean recomputed
  When the supervisor validates and issues the report
  Then PV number allocated, sealed PDF, QR verifies offline and online, status CURRENT
  And work item qty_reported = 4, execution state PARTIALLY_DELIVERED, client notified, portal shows the report

Scenario: report supersession detected by verification
  Given an issued report PV-…-0412
  When a new version is issued with reason "typo in structure part"
  Then PV-…-0412 status is SUPERSEDED by PV-…-0419
  And GET /verify/{token of 0412} returns SUPERSEDED with the new number
  And an altered copy of 0412's PDF fails PAdES validation

Scenario: milestone invoice and partial payment
  Given milestone 2 becomes INVOICEABLE on report issuance
  When finance issues an invoice from milestones 1 and 2
  Then the invoice number is the next gap-free number, total 60610.00, PDF sealed, client notified
  When a bank transfer of 30000.00 is recorded and allocated
  Then invoice paid_status is PARTIALLY_PAID, treasury account shows +30000.00, work items are PARTIALLY_PAID
  When the remainder is recorded
  Then paid_status is PAID, work items PAID, project can be closed once all items are delivered

Scenario: permissions hide commercial data
  Given a technician membership in department CONCRETE
  When the technician opens the project page
  Then the work breakdown tab shows items and states without unit prices or totals
  And the Quotes and Finance tabs are absent
  And GET /v1/projects/{id}/work-items returns no commercial fields (assert in API test, not UI)

Scenario: administrator adds a test without a release
  Given the admin console
  When the quality lead creates definition LOS_ANGELES with inputs, computed and rules, tests it in the sandbox and activates it
  And creates service LOS_ANGELES priced 45000 per sample
  Then the service is quotable, appears in the laboratory menu under Aggregates, and a run generates a worksheet and a generic report
```

## Appendix T — Default permission grid

Legend: V view · C create · E edit · S submit/approve/issue/sign as applicable · X delete/cancel · P print/export.
Scope in brackets: [B] own branch · [D] own department · [M] assigned to me · [A] own account · [*] all branches.
Field groups: −$ = without commercial group · $ = with commercial · £ = financial group.

| Resource | Commercial | Comm. manager | Lab reception | Technician | Lab supervisor | Finance | Assets | Branch manager | Tenant admin | Client user | Client admin |
|---|---|---|---|---|---|---|---|---|---|---|---|
| account | VCE$ [B] | VCE$ [B] | V−$ [B] | — | V−$ [B] | V£ [B] | V−$ [B] | V$£ [B] | — | V [A] | VE [A] |
| contact | VCE [B] | VCE [B] | V [B] | — | V [B] | V [B] | V [B] | V [B] | VCE [*] | V [A] | VCE [A] |
| project | VCE$ [B] | VCE$ [B] | V−$ [B] | V−$ [D,M] | V−$ [D] | V£ [B] | V−$ [B] | VE$£ [B] | — | V [A] | V [A] |
| task / work_item | VCE$ [B] | VCE$ [B] | VC−$ (variance) [B] | V−$ [M] | VC−$ [D] | V£ [B] | V−$ [B] | V$£ [B] | — | V [A] | V [A] |
| quote / revision | VCESP [B] | VCESP + approve/sign [B] | — | — | — | V [B] | — | VS [B] | — | V [A] | V [A] |
| acceptance | C (PAPER) [B] | C [B] | — | — | — | — | — | C [B] | — | C (PORTAL) [A] | C [A] |
| contract | VC [B] | VCS [B] | — | — | — | V [B] | — | VS [B] | — | V [A] | V [A] |
| order | V [B] | VE (amend) [B] | V−$ [B] | — | V−$ [D] | V [B] | V [B] | V [B] | — | V [A] | V [A] |
| expected_intake / intake | V [B] | V [B] | VCEP [B] | V [D] | VCEP [D] | — | — | V [B] | — | V [A] | V [A] |
| specimen / sample | — | — | VC + stage [B] | V + stage [D] | VCE + stage [D] | — | — | V [B] | — | V [A] | V [A] |
| test_run | — | — | V [B] | VE [M] | VCE assign/reassign/cancel [D] | — | — | V [B] | — | V (dates) [A] | V [A] |
| measurement | — | — | — | CE [M] | CE + override [D] | — | — | V [B] | — | — | — |
| report | V [B] | V [B] | V [B] | V [D] | VCS issue/print [D] | — | — | VS sign [B] | — | VP [A] | VP [A] |
| invoice / credit_note | V [B] | V [B] | — | — | — | VCESXP [B] | — | VS [B] | — | V [A] | V [A] |
| payment | — | — | — | — | — | VC + allocate [B] | — | V [B] | — | V [A] | V [A] |
| treasury_account / entry | — | — | — | — | — | VCE [B] | — | V [B] | configure | — | — |
| equipment / stock / consumable | — | — | — | V (pick instrument) [D] | V [D] | — | VCEXP [B] | V [B] | — | — | — |
| rental / sale / outing / transfer / maintenance / fleet | — | V [B] | — | — | — | V [B] | VCESXP [B] | VS [B] | — | V (own rentals) [A] | V [A] |
| work_order / phase | V [B] | V [B] | — | V [M] | VE [D] | — | — | VE [B] | — | V [A] | V [A] |
| attachment / comment | VC [B] | VC [B] | VC [B] | VC [M] | VC [D] | VC [B] | VC [B] | VC [B] | — | V (own) [A] | VC [A] |
| dashboard | V (commercial) [B] | V [B] | — | — | V (lab) [D] | V (finance) [B] | V (assets) [B] | V (all) [B] | V (all) [*] | — | — |
| configuration resources | — | — | — | — | — | — | — | V [B] | configure [*] | — | — |
| user / role / membership | — | — | — | — | — | — | — | V [B] | all [*] | — | VCE (own account users) [A] |
| audit_event | — | — | — | — | — | — | — | V [B] | V [*] | — | — |

The grid is a starting point; tenants edit it in the matrix screen. Tests generate one
authorisation case per cell (allowed / denied / scoped).

## Appendix U — UX writing and error rules

- **Language**: short, direct, present tense. French default, English parallel. Never
  technical jargon in user-facing text (no "entity", "payload", "null").
- **Buttons** name the outcome: "Issue report", "Record payment", "Send quote" — never
  "OK", "Submit". Destructive buttons name the object: "Cancel run", "Revoke report".
- **Empty states** say what the list is and offer the next action: "No intakes today. Start
  an intake."
- **Errors** are `message_key` + params rendered client-side; every key has FR and EN text
  and, when actionable, a link to the fix. Examples:
  `sales.quote.discount_requires_approval` → "This discount needs a manager's approval. Submit for approval?";
  `lab.intake.age_distribution_mismatch {distributed, total}` → "The distribution by age ({distributed}) does not match the number of specimens ({total}).";
  `lab.rule.blocked {rule}` → "A rule blocks this run: {rule}. Check the measurements.";
  `finance.invoice.gap_free_requires_issue` → "Invoice numbers are assigned when the invoice is issued.";
  `authz.forbidden {action}` → "You are not allowed to {action}. Ask an administrator.";
  `verify.not_found` → "No document matches this code. It may be a forgery: report it.".
- **Confirmations** state the consequence and the count: "Cancel 3 scheduled runs? The
  specimens will be released."
- **Success toasts** are specific: "Report PV-NKC-2026-0412 issued and sent to 2 contacts."
- **Numbers**: thousands separator and decimal per locale; currency code after the amount
  (MRU); dates `dd/MM/yyyy` (FR) and `yyyy-MM-dd` (EN); relative time for recent events.
- **Accessibility**: every icon-only button has a label; focus order follows reading
  order; colour never carries meaning alone (badges have text).

## Appendix V — Sizing model

| Load driver (per branch, per month) | Baseline | 10× scenario | Effect |
|---|---|---|---|
| Quotes | 500 | 5 000 | negligible CPU; PDF renders ≈ 1 s each in a worker |
| Intakes | 1 000 | 10 000 | labels ≈ 10 000–100 000 ZPL jobs; trivial |
| Specimens / measurements | 10 000 / 30 000 | 100 000 / 300 000 | ~50 MB/month of rows at 10×; indexes fine |
| Reports | 2 000 | 20 000 | 20 000 renders + seals ≈ 6 worker-hours/month; 2 workers |
| Documents storage | ~2 GB/year | ~20 GB/year | object storage; backups sized accordingly |
| Portal users | 200 | 2 000 | SSE connections; one API replica handles ~10 000 idle streams |
| API requests | ~1 M | ~10 M | one Django/Granian instance sustains ~200–400 req/s on 1 vCPU for typical reads; Cloud Run autoscales by concurrency, so 10× means a handful of instances at peak hours and one at night |
| Database | 4 GB | 40 GB | single PostgreSQL with 8–16 GB RAM up to 10×; add replica for dashboards beyond |

Rule of thumb: the baseline Cloud Run configuration (api min 1 / max 10, worker min 1 / max 5,
Cloud SQL 2 vCPU / 8 GB) serves a tenant at 10× baseline by autoscaling; the second branch or
tenant adds data and instances, not architecture.

## Appendix W — Register of configurable parameters (nothing hard-coded)

Every parameter below is data, editable in the admin console (scope in brackets). If a
future feature needs a value not in this register, the register is extended before the
code is written.

| Area | Parameter | Scope |
|---|---|---|
| Identity | password policy, session lifetime, MFA requirement per role, lockout thresholds, OTP length/expiry/attempts, allowed e-mail domains for staff | Tenant |
| Branding | logo (SVG), primary colour, document header/footer texts, e-mail signature, favicon | Tenant / Branch override |
| Organisation | branches, departments, working days, holidays, timezone, default locales, currency, rounding rule | Branch |
| Numbering | one scheme per document kind (pattern, reset, gap policy, allocation), reservations | Branch (+ Department) |
| Vocabularies | every list of §10.2, labels per locale, colours, order | Tenant / Branch |
| Workflows | states (names, colours, semantics), transitions, required actions, guards, effects, SLA days | Kind × Branch |
| Catalog | categories, services and kinds, units of sale, test definitions (all fields), specimen types and geometry, sieve sets, materials, natures, phase templates, equipment classes | Tenant / Branch |
| Test rules | rule expressions and parameters (e.g. outlier threshold 5 MPa), allowed ages, turnaround days, stages and locations, intake fields | Definition version |
| Pricing | price lists, validity, tier and account overrides, tax rules and rates, exemptions, discount approval threshold, default quote validity days | Branch / Account |
| Payment terms | templates (milestones, triggers, due days), default template, who may customise per quote | Branch |
| Signatures | signatories per document kind, mode (image/drawn/certificate/external), image assets and positions, signing order, step-up requirement | Branch |
| Documents | templates per kind and locale, print profiles (defaults for signature image, digital signature, QR, watermark, paper, copies), label formats and sizes, watermark texts | Branch |
| Verification | public digest exposure behind short code (on/off), verification page texts, transparency publication schedule | Tenant |
| Notifications | rules, audiences, channels, message templates per locale, quiet hours, digest schedules, provider credentials, fallback channel order | Branch |
| Portal | features per account, welcome texts, terms version, which states clients see, request types | Tenant / Account |
| Laboratory | daily capacity per department, default instrument per definition, label printer per station, offline cache window (days), reviewer ≠ entrant rule | Branch / Department |
| Finance | invoice due days, dunning schedule and levels, cash-close approval threshold, treasury accounts printed on invoices, invoice legal mentions, late-rental penalty rule | Branch |
| Assets | stock thresholds, reservation expiry, rental units and rates, maintenance intervals, condition vocabulary | Branch |
| Delivery | responsible categories, phase weights and deadlines per template | Tenant |
| Analytics | dashboard KPI selection per role, ageing buckets, target strength defaults | Tenant |
| Data lifecycle | draft purge age, export formats, anonymisation policy | Tenant |
| Integrations | e-mail, SMS, WhatsApp, e-signature, payment providers, accounting export mapping, storage settings | Tenant |

*End of specification. Changes are made by issuing a new numbered version of this file with a
dated change summary at the top.*
