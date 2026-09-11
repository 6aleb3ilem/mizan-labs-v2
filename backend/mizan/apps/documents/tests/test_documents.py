"""SPEC §18 and Appendix S: a sealed PDF/A verifies offline (QR) and online (registry); an altered copy fails."""

from __future__ import annotations

import io
from typing import Any

import pytest
from django.test import Client

from mizan.apps.audit.models import AuditEvent
from mizan.apps.documents import issuance, keys, qr, transparency
from mizan.apps.documents.defaults import install_default_templates
from mizan.apps.documents.models import FraudCase, IssuedDocument, VerificationAttempt
from mizan.apps.documents.signing import validate_seal
from mizan.platform.db.tenancy import platform_scope

pytestmark = pytest.mark.django_db

PASSWORD = "Passw0rd!Passw0rd"

PV_DATA: dict[str, Any] = {
    "account": {"legal_name": "SOGECO"},
    "project": {
        "number": "AF-2026-0031",
        "title": "Immeuble R+4 Tevragh Zeina",
        "location": "Tevragh Zeina",
    },
    "intake": {
        "number": "RC-26-0412",
        "received_at": "2026-09-11",
        "fields": {
            "fabrication_date": "2026-09-10",
            "structure_part": "Semelles S1-S4",
            "sampling_by": "LAB",
            "slump_cm": 8,
            "site": "Tevragh Zeina",
            "mix_design": {
                "cement": {"name": "CEM II 42.5", "dosage": 350},
                "water": {"name": "Eau", "dosage": 175},
            },
        },
    },
    "run": {
        "tested_at": "2026-10-08",
        "age": 28,
        "specimens": [
            {
                "ref": "1",
                "specimen_type": "CYL 16x32",
                "weight_kg": "12.41",
                "load_kgf": 45210,
                "stress_kgcm2": 225,
                "stress_mpa": "22.5",
                "excluded": False,
            },
            {
                "ref": "2",
                "specimen_type": "CYL 16x32",
                "weight_kg": "12.38",
                "load_kgf": 46800,
                "stress_kgcm2": 233,
                "stress_mpa": "23.3",
                "excluded": False,
            },
            {
                "ref": "3",
                "specimen_type": "CYL 16x32",
                "weight_kg": "12.45",
                "load_kgf": 30000,
                "stress_kgcm2": 149,
                "stress_mpa": "14.9",
                "excluded": True,
            },
            {
                "ref": "4",
                "specimen_type": "CYL 16x32",
                "weight_kg": "12.40",
                "load_kgf": 45500,
                "stress_kgcm2": 226,
                "stress_mpa": "22.6",
                "excluded": False,
            },
        ],
        "n_tested": 3,
        "mean_mpa": "22.8",
        "notes": ["Éprouvette 3 écartée (écart ≥ 5 MPa)"],
        "operator": "Sidi",
        "instrument": "Presse 1",
        "reviewer": "Fatimetou",
    },
    "report": {"version": 1},
}


@pytest.fixture
def ready(branch: Any) -> Any:
    install_default_templates()
    keys.ensure_branch_keys(branch)
    return branch


def _issue(branch: Any, number: str = "PV-NKC-2026-0412", **overrides: Any) -> IssuedDocument:
    request = issuance.IssueRequest(
        kind="REPORT",
        template_kind="PV_CONCRETE",
        number=number,
        branch=branch,
        data=PV_DATA,
        subject={"acc": "SOGECO", "prj": "AF-2026-0031"},
        digest={"n": 3, "age": 28, "mean": "22.8", "u": "MPa", "excluded": 1},
        subject_type="report",
        locale="fr",
    )
    for key, value in overrides.items():
        setattr(request, key, value)
    return issuance.issue_document(request)


def _pdfa_marker_present(pdf: bytes) -> bool:
    from pypdf import PdfReader

    xmp = PdfReader(io.BytesIO(pdf)).xmp_metadata
    return xmp is not None and b"pdfaid" in xmp.stream.get_data()


def test_issued_document_is_sealed_pdfa_and_registered(ready: Any) -> None:
    document = _issue(ready)
    pdf = issuance.original_pdf(document)
    assert pdf.startswith(b"%PDF-1.7") and document.pdf_size == len(pdf)
    assert _pdfa_marker_present(pdf)
    status = validate_seal(pdf, [document.seal_key.certificate_pem])  # type: ignore[union-attr]
    assert status.valid and status.intact and status.trusted and status.coverage == "ENTIRE_FILE"
    assert document.seal_level == "B-B"
    assert (
        document.status == "CURRENT"
        and len(document.verify_token) == 26
        and len(document.short_code) == 7
    )
    assert document.transparency_leaf_index == 0
    assert AuditEvent.objects.filter(
        aggregate_type="issued_document", aggregate_id=document.id, action="issued"
    ).exists()


def test_altered_copy_fails_seal_validation(ready: Any) -> None:
    document = _issue(ready)
    pdf = issuance.original_pdf(document)
    tampered = bytearray(pdf)
    position = pdf.find(b"stream\n") + 20
    tampered[position] ^= 0xFF
    status = validate_seal(bytes(tampered), [document.seal_key.certificate_pem])  # type: ignore[union-attr]
    assert status.intact is False and status.valid is False
    assert (
        validate_seal(pdf, ["-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n"]).valid
        is False
    )


def test_qr_payload_verifies_offline_with_the_published_keys(ready: Any) -> None:
    document = _issue(ready)
    with platform_scope():
        jwks = keys.public_jwks()
    payload = qr.verify_payload(document.qr_jws, jwks)
    assert (
        payload["v"] == 1 and payload["kind"] == "REPORT" and payload["num"] == "PV-NKC-2026-0412"
    )
    assert (
        payload["sub"] == {"acc": "SOGECO", "prj": "AF-2026-0031"}
        and payload["dg"]["mean"] == "22.8"
    )
    assert payload["t"] == document.verify_token and payload["h"] == qr.hash_prefix(
        document.content_hash
    )
    assert payload["iss"] == "T1/NKC"
    with pytest.raises(qr.InvalidQr):
        qr.verify_payload(document.qr_jws[:-4] + "AAAA", jwks)
    assert Client().get("/api/v1/verify/keys").json()["keys"][0]["kty"] == "OKP"


def test_content_hash_is_deterministic(ready: Any) -> None:
    first = _issue(ready, number="PV-1")
    second = _issue(ready, number="PV-2")
    assert first.content_hash == second.content_hash
    other = _issue(
        ready, number="PV-3", data={**PV_DATA, "run": {**PV_DATA["run"], "mean_mpa": "23.0"}}
    )
    assert other.content_hash != first.content_hash


def test_public_verification_steps(ready: Any) -> None:
    document = _issue(ready)
    client = Client()
    step1 = client.get(f"/api/v1/verify/{document.verify_token}")
    assert step1.status_code == 200, step1.content
    body = step1.json()
    assert (
        body["status"] == "CURRENT"
        and body["number"] == "PV-NKC-2026-0412"
        and body["branch"] == "NKC"
    )
    assert body["pdf_sha256"] == document.pdf_sha256 and body["subject"]["acc"] == "SOGECO"

    wrong = client.post(
        f"/api/v1/verify/{document.verify_token}/digest",
        data={"short_code": "ZZZZ-ZZ"},
        content_type="application/json",
    )
    assert wrong.status_code == 404
    ok = client.post(
        f"/api/v1/verify/{document.verify_token}/digest",
        data={"short_code": document.short_code.lower()},
        content_type="application/json",
    )
    assert ok.status_code == 200 and ok.json()["digest"] == {
        "n": 3,
        "age": 28,
        "mean": "22.8",
        "u": "MPa",
        "excluded": 1,
    }
    for _ in range(3):
        client.post(
            f"/api/v1/verify/{document.verify_token}/digest",
            data={"short_code": document.short_code},
            content_type="application/json",
        )
    limited = client.post(
        f"/api/v1/verify/{document.verify_token}/digest",
        data={"short_code": document.short_code},
        content_type="application/json",
    )
    assert limited.status_code == 429

    assert client.get("/api/v1/verify/NOPE7K2MQ9X3ABCDEFGHIJKLMN").status_code == 404
    with platform_scope():
        outcomes = list(
            VerificationAttempt.objects.order_by("at").values_list("outcome", flat=True)
        )
    assert (
        outcomes[:3] == ["FOUND", "DIGEST_BAD", "DIGEST_OK"]
        and outcomes[-1] == "NOT_FOUND"
        and "RATE_LIMITED" in outcomes
    )


def test_supersession_and_revocation_are_visible_online(ready: Any) -> None:
    old = _issue(ready, number="PV-NKC-2026-0412")
    new = _issue(ready, number="PV-NKC-2026-0419")
    issuance.supersede(old, new, "typo in structure part")
    body = Client().get(f"/api/v1/verify/{old.verify_token}").json()
    assert body["status"] == "SUPERSEDED" and body["superseded_by"] == "PV-NKC-2026-0419"
    issuance.revoke(new, "issued to the wrong project")
    body = Client().get(f"/api/v1/verify/{new.verify_token}").json()
    assert body["status"] == "REVOKED" and body["revoked_reason"] == "issued to the wrong project"
    with platform_scope():
        assert VerificationAttempt.objects.filter(
            token=new.verify_token, outcome="REVOKED_LOOKUP"
        ).exists()


def test_transparency_log_and_signed_head(ready: Any) -> None:
    documents = [_issue(ready, number=f"PV-{i}") for i in range(3)]
    size, root = transparency.current_root()
    assert size == 3
    for index, _document in enumerate(documents):
        proof = transparency.proof_for(index)
        assert proof["root_hash"] == root
        assert transparency.verify_inclusion(
            bytes.fromhex(proof["leaf_hash"]),
            index,
            size,
            [bytes.fromhex(p) for p in proof["proof"]],
            bytes.fromhex(root),
        )
    assert not transparency.verify_inclusion(b"\x00" * 32, 0, size, [], bytes.fromhex(root))
    qr_key = keys.active_key(ready.id, "QR")
    assert qr_key is not None
    head = transparency.publish_head(qr_key)
    with platform_scope():
        jwks = keys.public_jwks()
    signed = qr.verify_payload(head.signature, jwks)
    assert signed["size"] == 3 and signed["root"] == root
    client = Client()
    assert client.get("/api/v1/verify/transparency/head?tenant_code=T1").json()["tree_size"] == 3
    proof = client.get(f"/api/v1/verify/transparency/proof/{documents[1].verify_token}").json()
    assert proof["index"] == 1 and proof["tree_size"] == 3


def test_renditions_and_downloads_require_permissions(ready: Any, make_member: Any) -> None:
    document = _issue(ready)
    supervisor, _ = make_member("LAB_SUPERVISOR", department_id=None)
    commercial, _ = make_member("COMMERCIAL")
    technician, _ = make_member("TECHNICIAN")

    def api(user: Any) -> Client:
        token = (
            Client()
            .post(
                "/api/v1/auth/login",
                data={"email": user.email, "password": PASSWORD},
                content_type="application/json",
            )
            .json()["access_token"]
        )
        return Client(HTTP_AUTHORIZATION=f"Bearer {token}")

    assert api(commercial).get(f"/api/v1/documents/{document.id}").status_code == 200  # report.view
    assert (
        api(commercial)
        .post(
            f"/api/v1/documents/{document.id}/renditions",
            data={"watermark": "COPY"},
            content_type="application/json",
        )
        .status_code
        == 403
    )  # no report.print
    download = api(technician).get(f"/api/v1/documents/{document.id}/download")
    assert download.status_code == 200 and download["Content-Type"] == "application/pdf"
    rendition = api(supervisor).post(
        f"/api/v1/documents/{document.id}/renditions",
        data={"watermark": "COPY", "signature_image": True},
        content_type="application/json",
    )
    assert rendition.status_code == 201, rendition.content
    body = rendition.json()
    assert body["options"]["watermark"] == "COPY" and body["sha256"] != document.pdf_sha256
    downloaded = api(supervisor).get(f"/api/v1/documents/{document.id}/renditions/{body['id']}")
    assert downloaded.status_code == 200
    assert validate_seal(downloaded.content, [document.seal_key.certificate_pem]).valid  # type: ignore[union-attr]
    assert (
        api(supervisor).get(f"/api/v1/verify/{document.verify_token}/original").status_code == 200
    )


def test_suspicious_report_opens_a_fraud_case(ready: Any) -> None:
    document = _issue(ready)
    client = Client()
    known = client.post(
        f"/api/v1/verify/{document.verify_token}/report-suspicious",
        data={"reporter_contact": "ahmed@client.dev", "message": "numbers differ from my copy"},
        content_type="application/json",
    )
    assert known.status_code == 201
    unknown = client.post(
        "/api/v1/verify/UNKNOWNTOKEN/report-suspicious",
        data={"message": "looks fake"},
        content_type="application/json",
    )
    assert unknown.status_code == 201
    with platform_scope():
        assert FraudCase.objects.filter(document=document).count() == 1
        assert FraudCase.objects.filter(tenant_id__isnull=True, token="UNKNOWNTOKEN").count() == 1


def test_template_administration(make_member: Any, ready: Any) -> None:
    admin, _ = make_member("TENANT_ADMIN", all_branches=True)
    token = (
        Client()
        .post(
            "/api/v1/auth/login",
            data={"email": admin.email, "password": PASSWORD},
            content_type="application/json",
        )
        .json()["access_token"]
    )
    api = Client(HTTP_AUTHORIZATION=f"Bearer {token}")
    listed = api.get("/api/v1/document-templates?kind=PV_CONCRETE").json()
    assert {t["locale"] for t in listed} == {"fr", "en"} and all(
        t["status"] == "ACTIVE" for t in listed
    )
    broken = api.post(
        "/api/v1/document-templates",
        data={"kind": "RECEIPT", "html": "<p>{{ document.number }</p>"},
        content_type="application/json",
    )
    assert broken.status_code == 422
    created = api.post(
        "/api/v1/document-templates",
        data={
            "kind": "RECEIPT",
            "html": "<p>{{ document.number }} {{ amount }}</p>",
            "sample_data": {"amount": "30000"},
        },
        content_type="application/json",
    )
    assert created.status_code == 201, created.content
    preview = api.post(
        f"/api/v1/document-templates/{created.json()['id']}:preview",
        data={},
        content_type="application/json",
    )
    assert preview.status_code == 200 and preview["Content-Type"] == "application/pdf"
    v2 = api.post(
        f"/api/v1/document-templates/{created.json()['id']}/versions",
        data={"html": "<p>v2 {{ document.number }}</p>"},
        content_type="application/json",
    )
    assert v2.status_code == 201 and v2.json()["version"] == 2
    approved = api.post(f"/api/v1/document-templates/{v2.json()['id']}:approve").json()
    assert approved["status"] == "ACTIVE"
    assert api.get(f"/api/v1/document-templates/{created.json()['id']}").json()["status"] == "DRAFT"
    profile = api.post(
        "/api/v1/print-profiles",
        data={
            "branch_id": str(ready.id),
            "kind": "RECEIPT",
            "defaults": {"qr": True, "signature_image": False},
        },
        content_type="application/json",
    )
    assert profile.status_code == 201
