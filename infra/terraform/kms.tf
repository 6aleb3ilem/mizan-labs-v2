resource "google_kms_key_ring" "signing" {
  name       = "${local.name}-signing"
  location   = var.region
  depends_on = [google_project_service.apis]
}

# One PDF seal key (RSA-3072, HSM) and one QR key (Ed25519) for the first branch; further
# branches are added by the platform console through the same module.
resource "google_kms_crypto_key" "pdf_seal" {
  name     = "branch-nkc-pdf"
  key_ring = google_kms_key_ring.signing.id
  purpose  = "ASYMMETRIC_SIGN"
  version_template {
    algorithm        = "RSA_SIGN_PKCS1_3072_SHA256"
    protection_level = "HSM"
  }
  lifecycle { prevent_destroy = true }
}

resource "google_kms_crypto_key" "qr" {
  name     = "branch-nkc-qr"
  key_ring = google_kms_key_ring.signing.id
  purpose  = "ASYMMETRIC_SIGN"
  version_template {
    algorithm        = "EC_SIGN_ED25519"
    protection_level = "SOFTWARE"
  }
  lifecycle { prevent_destroy = true }
}

resource "google_kms_crypto_key_iam_member" "api_signer" {
  for_each      = { pdf = google_kms_crypto_key.pdf_seal.id, qr = google_kms_crypto_key.qr.id }
  crypto_key_id = each.value
  role          = "roles/cloudkms.signerVerifier"
  member        = "serviceAccount:${google_service_account.api.email}"
}

resource "google_kms_crypto_key_iam_member" "worker_signer" {
  for_each      = { pdf = google_kms_crypto_key.pdf_seal.id, qr = google_kms_crypto_key.qr.id }
  crypto_key_id = each.value
  role          = "roles/cloudkms.signerVerifier"
  member        = "serviceAccount:${google_service_account.worker.email}"
}
