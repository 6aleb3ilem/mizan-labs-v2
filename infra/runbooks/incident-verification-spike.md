# Runbook — Incident: verification spike

1. Inspect the verification attempts (outcome, IP hash, user agent) for the document token.
2. If the document is genuine and altered copies circulate: revoke it (reason), issue a new
   version, notify the account through the portal and by e-mail.
3. Open or update the fraud case; export the attempts as evidence.
4. Tighten the Cloudflare rate limit temporarily if the spike is abusive.
