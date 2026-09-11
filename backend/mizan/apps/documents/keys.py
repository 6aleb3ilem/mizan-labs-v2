"""Branch signing keys: Ed25519 for QR payloads, RSA-3072 X.509 for PDF seals (SPEC §18.7).

Development keeps private material in ``MIZAN_SIGNING_LOCAL_DIR``; production points
``key_ref`` at a KMS resource and uses the KMS backends behind the same interfaces.
"""

from __future__ import annotations

import datetime as dt
import json
import secrets
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone
from joserfc.jwk import OKPKey

from mizan.apps.documents.models import KeyPurpose, KeyStatus, SigningKey
from mizan.apps.documents.signing import (
    KmsSigner,
    LocalPemSigner,
    PdfSigner,
    generate_self_signed_certificate,
)


def _local_dir() -> Path:
    path = Path(settings.MIZAN_SIGNING_LOCAL_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _new_kid(branch_code: str, purpose: str) -> str:
    return f"{branch_code.lower()}-{purpose.lower()}-{timezone.now():%Y%m}-{secrets.token_hex(3)}"


def create_qr_key(branch: Any) -> SigningKey:
    kid = _new_kid(branch.code, "qr")
    key = OKPKey.generate_key("Ed25519", parameters={"kid": kid})
    if settings.MIZAN_SIGNING_BACKEND != "local":
        raise NotImplementedError("KMS-backed QR keys are provisioned by the rotate-key runbook")
    path = _local_dir() / f"{kid}.json"
    path.write_text(json.dumps(key.as_dict(private=True)))
    path.chmod(0o600)
    created: SigningKey = SigningKey.objects.create(
        branch=branch,
        purpose=KeyPurpose.QR,
        kid=kid,
        algorithm="EdDSA",
        backend="local",
        key_ref=str(path),
        public_jwk={**key.as_dict(private=False), "use": "sig", "alg": "EdDSA"},
    )
    return created


def create_seal_key(branch: Any) -> SigningKey:
    kid = _new_kid(branch.code, "pdf")
    if settings.MIZAN_SIGNING_BACKEND != "local":
        raise NotImplementedError("KMS-backed seal keys are provisioned by the rotate-key runbook")
    key_path, cert_path, cert_pem = generate_self_signed_certificate(
        common_name=f"{branch.legal_name} — document seal",
        organisation=branch.legal_name,
        out_dir=_local_dir(),
        kid=kid,
    )
    created: SigningKey = SigningKey.objects.create(
        branch=branch,
        purpose=KeyPurpose.PDF,
        kid=kid,
        algorithm="RS256",
        backend="local",
        key_ref=str(key_path),
        certificate_pem=cert_pem,
        public_jwk={"cert_path": str(cert_path)},
    )
    return created


def active_key(branch_id: Any, purpose: str) -> SigningKey | None:
    key: SigningKey | None = (
        SigningKey.objects.filter(branch_id=branch_id, purpose=purpose, status=KeyStatus.ACTIVE)
        .order_by("-valid_from")
        .first()
    )
    return key


def ensure_branch_keys(branch: Any) -> tuple[SigningKey, SigningKey]:
    qr = active_key(branch.id, KeyPurpose.QR) or create_qr_key(branch)
    seal = active_key(branch.id, KeyPurpose.PDF) or create_seal_key(branch)
    return qr, seal


def load_qr_private_key(key: SigningKey) -> OKPKey:
    if key.backend != "local":
        raise NotImplementedError("KMS-backed QR signing is not available in this environment")
    data = json.loads(Path(key.key_ref).read_text())
    return OKPKey.import_key(data)


def pdf_signer_for(key: SigningKey) -> PdfSigner:
    if key.backend == "local":
        return LocalPemSigner(key.key_ref, str(key.public_jwk.get("cert_path", "")))
    return KmsSigner(key.key_ref, key.certificate_pem)


def public_jwks(tenant_scoped: bool = False) -> dict[str, Any]:
    """JWKS of active and recently retired QR keys (SPEC §18.5)."""
    keys = SigningKey.objects.filter(purpose=KeyPurpose.QR).order_by("-valid_from")
    return {"keys": [k.public_jwk for k in keys if k.public_jwk]}


def rotate(branch: Any, purpose: str) -> SigningKey:
    """Create a new active key; the previous one stays valid for verification (90-day overlap)."""
    previous = active_key(branch.id, purpose)
    new = create_qr_key(branch) if purpose == KeyPurpose.QR else create_seal_key(branch)
    if previous is not None:
        previous.status = KeyStatus.RETIRED
        previous.valid_to = timezone.now() + dt.timedelta(days=90)
        previous.save(update_fields=["status", "valid_to"])
    return new
