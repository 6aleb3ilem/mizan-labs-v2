# Runbook — Rotate a signing key

1. Create the new key version in Cloud KMS (`branch-<code>-pdf` or `branch-<code>-qr`).
2. Publish the new public key: the platform console registers it (`signing_key` row, status
   ACTIVE) while the old one stays valid for verification; the JWKS lists both.
3. Switch the branch signer to the new key (issuance uses the active key of the purpose).
4. Keep the old key for verification for ten years; never destroy a KMS key version that
   signed a document.
5. Verify a freshly issued document offline (QR) and online (registry) and an old one.
