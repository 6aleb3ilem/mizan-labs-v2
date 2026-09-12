# Runbook — Incident: failed notifications

1. Admin console → Notifications → Delivery log filtered on status FAILED (or the health page).
2. Read the last error: provider rejection (permanent) vs network (transient, already retried
   five times with backoff).
3. Check the provider status (SMTP relay, SMS aggregator, WhatsApp Cloud API) and the
   configuration in the environment (`backend/mizan/config/env.py`).
4. Retry the batch from the delivery log once the provider is back; fallback channels have
   already been attempted in the branch order (WhatsApp → SMS → e-mail).
5. If a template renders wrongly, fix it in Message templates (preview) and retry.
