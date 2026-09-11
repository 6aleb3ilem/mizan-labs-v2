"""PDF sealing and validation with pyHanko (SPEC §18.1, §18.7, ADR 0004)."""

from __future__ import annotations

import datetime as dt
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

log = logging.getLogger("mizan.documents.signing")


@dataclass(frozen=True, slots=True)
class SealStatus:
    valid: bool
    intact: bool
    trusted: bool
    coverage: str
    signer: str
    level: str
    error: str = ""


class PdfSigner(Protocol):
    certificate_pem: str

    def sign(
        self, pdf: bytes, *, reason: str, location: str, tsa_url: str | None, field_name: str
    ) -> tuple[bytes, str]: ...


class LocalPemSigner:
    """Signs with a PEM key pair on disk (development and tests)."""

    def __init__(self, key_path: str | Path, cert_path: str | Path) -> None:
        self.key_path = Path(key_path)
        self.cert_path = Path(cert_path)
        self.certificate_pem = self.cert_path.read_text()

    def sign(
        self, pdf: bytes, *, reason: str, location: str, tsa_url: str | None, field_name: str
    ) -> tuple[bytes, str]:
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
        from pyhanko.sign import signers
        from pyhanko.sign.fields import SigSeedSubFilter

        signer = signers.SimpleSigner.load(  # type: ignore[no-untyped-call]
            str(self.key_path), str(self.cert_path), key_passphrase=None
        )
        timestamper: Any = None
        level = "B-B"
        if tsa_url:
            from pyhanko.sign.timestamps import HTTPTimeStamper

            timestamper = HTTPTimeStamper(tsa_url)
            level = "B-T"
        meta = signers.PdfSignatureMetadata(
            field_name=field_name,
            subfilter=SigSeedSubFilter.PADES,
            md_algorithm="sha256",
            reason=reason,
            location=location,
        )
        writer = IncrementalPdfFileWriter(io.BytesIO(pdf))
        output = signers.sign_pdf(writer, meta, signer=signer, timestamper=timestamper)
        return output.getvalue(), level


class KmsSigner:
    """Placeholder for the cloud KMS signer (SPEC §18.7): same interface, keys never leave the KMS."""

    def __init__(self, key_ref: str, certificate_pem: str) -> None:
        self.key_ref = key_ref
        self.certificate_pem = certificate_pem

    def sign(
        self, pdf: bytes, *, reason: str, location: str, tsa_url: str | None, field_name: str
    ) -> tuple[bytes, str]:
        raise NotImplementedError(
            "KMS signing is configured per deployment (see infra/runbooks/signing-keys.md)"
        )


def generate_self_signed_certificate(
    *,
    common_name: str,
    organisation: str,
    out_dir: Path,
    kid: str,
    key_size: int = 3072,
    days: int = 3650,
) -> tuple[Path, Path, str]:
    """Development certificate for the branch seal; production uses the tenant root CA in the KMS."""
    out_dir.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organisation),
        ]
    )
    now = dt.datetime.now(dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    key_path = out_dir / f"{kid}.key.pem"
    cert_path = out_dir / f"{kid}.cert.pem"
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    cert_path.write_text(cert_pem)
    return key_path, cert_path, cert_pem


def seal_pdf(
    pdf: bytes, signer: PdfSigner, *, reason: str, location: str, tsa_url: str | None = None
) -> tuple[bytes, str]:
    return signer.sign(
        pdf, reason=reason, location=location, tsa_url=tsa_url, field_name="BranchSeal"
    )


def validate_seal(pdf: bytes, trust_roots_pem: list[str]) -> SealStatus:
    """Validate the first embedded signature against the given certificates."""
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.general import load_certs_from_pemder_data
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext

    try:
        roots = [
            cert for pem in trust_roots_pem for cert in load_certs_from_pemder_data(pem.encode())
        ]
        reader = PdfFileReader(io.BytesIO(pdf))
        signatures = reader.embedded_signatures
        if not signatures:
            return SealStatus(False, False, False, "NONE", "", "", "no signature")
        status = validate_pdf_signature(
            signatures[0], ValidationContext(trust_roots=roots, allow_fetching=False)
        )
        signer_name = ""
        cert = getattr(status, "signing_cert", None)
        if cert is not None:
            signer_name = cert.subject.human_friendly
        return SealStatus(
            valid=bool(status.bottom_line),
            intact=bool(status.intact),
            trusted=bool(status.trusted),
            coverage=str(getattr(status.coverage, "name", status.coverage)),
            signer=signer_name,
            level="B-T" if getattr(status, "timestamp_validity", None) else "B-B",
        )
    except Exception as exc:
        log.info("seal validation failed: %s", exc)
        return SealStatus(False, False, False, "NONE", "", "", str(exc)[:200])
