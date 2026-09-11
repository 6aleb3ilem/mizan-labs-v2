# ADR 0004 — What the QR binds, and which PAdES level is applied where

Date: 2026-09-11 · Status: accepted

## Context
SPEC §18.4 puts ``"h": <first 16 bytes of pdf_sha256>`` in the signed QR payload, and §18.3
prints that QR inside the PDF. A file cannot contain its own hash: sealing and embedding the
QR change the bytes the hash would cover. SPEC §18.1 also asks for PAdES-B-LTA with an RFC 3161
timestamp, which needs a timestamp authority that does not exist in development or tests.

## Decision
- The QR payload's ``h`` is the first 16 bytes of the **content hash**: SHA-256 of the
  canonical JSON of ``{template id, template version, locale, data}``. It is deterministic
  (same template version and data give the same hash, SPEC §18.1) and is computed before the
  PDF exists. The registry stores both the content hash and the SHA-256 of the sealed PDF;
  ``GET /verify/{token}`` returns the PDF hash so anyone holding a file can compare it.
- Offline verification checks the Ed25519 signature of the QR against the published JWKS and
  shows the payload fields for side-by-side comparison with the paper. Online verification
  additionally reports the registry status (CURRENT / SUPERSEDED / REVOKED) and the PDF hash.
- The branch seal is applied at PAdES-B-B in environments without a timestamp authority and
  at B-T / B-LTA when ``TSA_URL`` is configured. Validation embeds nothing that the environment
  cannot provide. The level actually applied is recorded on the issued document.
- Development and test signing keys are generated locally (Ed25519 JWK for the QR, RSA-3072
  self-signed certificate for the seal) under ``var/keys``; production keys live in Cloud KMS
  behind the same ``PdfSigner`` and ``QrSigner`` interfaces (SPEC §18.7).

## Consequences
Every issued PDF still verifies offline (signature) and online (registry), and any alteration
of the sealed file is detected by PAdES validation; the QR additionally proves that the
document content, not just the file, is the one the laboratory issued.
