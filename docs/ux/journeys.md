# Journey maps and time-on-task targets (SPEC §21.8, Appendix S)

| Journey | Persona | Steps | Target | Measured how |
|---|---|---|---|---|
| Quote from an existing project | Aïcha | open project → work breakdown → "Create quote from unquoted items" → discount, milestones → send | < 5 min | Playwright timing on the golden path; UI analytics `quote.create` funnel |
| Intake of 16 specimens | Moussa | scan project / pick expected intake → specimens with ages → delivered-by, photos → save & print labels | < 3 min | tablet usability sessions; `intake.register` timing |
| Worksheet for 4 specimens | Sidi | scan label → inputs by level → live computed → mark measured | < 90 s | offline scenario timing (`sync/measurements`) |
| Issue a report | Fatimetou | review queue → draft preview → validate → issue and send | < 60 s | `report.issue` timing; document pipeline p95 |
| Record a payment | Mohamed | invoice → record payment → allocate → receipt | < 45 s | `payment.record` timing |
| Accept a quote (portal) | Ahmed | notification → quote → accept with OTP | < 2 min | portal analytics |
| Verify a document | Anyone | scan QR → status → short code → digest | < 20 s | verify site timing, offline check |
| Add a test (no release) | Admin | definition editor → sandbox → activate → service & price | < 30 min | admin usability sessions |

Usability testing every two weeks during Phases 1–3 with real staff on real devices; findings
become tickets; the metric dashboard (task success, time, errors) is reviewed by the product
owner. Design reviews check: primary action obvious, ≤ 7 visible controls by default, state
visible, error recoverable, works offline where required, keyboard complete, contrast
validated, both languages fit without truncation.
