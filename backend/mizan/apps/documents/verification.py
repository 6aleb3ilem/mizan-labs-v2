"""Public verification (SPEC §18.5, §18.6): lookups, digests behind the short code, detection."""

from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.utils import timezone

from mizan.apps.documents.models import (
    DocumentStatus,
    FraudCase,
    IssuedDocument,
    VerificationAttempt,
    VerificationOutcome,
)
from mizan.apps.documents.tokens import hash_ip, normalise_short_code
from mizan.platform.api.errors import NotFound, TooManyRequests
from mizan.platform.db.tenancy import platform_scope, tenant_scope
from mizan.platform.events import emit

DIGEST_RATE = 5  # per minute per IP
SUSPICIOUS_UNKNOWN = 10  # unknown tokens from one IP in 10 minutes


def _record(
    token: str,
    outcome: str,
    *,
    ip: str | None,
    user_agent: str,
    tenant_id: Any = None,
    short_code: str = "",
) -> None:
    with platform_scope():
        VerificationAttempt.objects.create(
            tenant_id=tenant_id,
            token=token[:32],
            short_code_given=short_code[:8],
            ip_hash=hash_ip(ip),
            user_agent=user_agent[:256],
            outcome=outcome,
        )


def _find(token: str) -> IssuedDocument | None:
    with platform_scope():
        document: IssuedDocument | None = (
            IssuedDocument.objects.select_related("branch", "superseded_by")
            .filter(verify_token=token)
            .first()
        )
    return document


def _suspicious_check(ip: str | None) -> None:
    key = f"verify:unknown:{hash_ip(ip)}"
    count = cache.get(key, 0) + 1
    cache.set(key, count, timeout=600)
    if count == SUSPICIOUS_UNKNOWN:
        emit(
            "verification.suspicious",
            aggregate_type="verification",
            payload={"ip_hash": hash_ip(ip), "unknown_tokens": count},
            tenant_id=None,
        )


def lookup(token: str, *, ip: str | None, user_agent: str = "") -> dict[str, Any]:
    document = _find(token)
    if document is None:
        _record(token, VerificationOutcome.NOT_FOUND, ip=ip, user_agent=user_agent)
        _suspicious_check(ip)
        raise NotFound("verify.not_found", code="verify_not_found")
    outcome = (
        VerificationOutcome.REVOKED_LOOKUP
        if document.status == DocumentStatus.REVOKED
        else VerificationOutcome.FOUND
    )
    _record(token, outcome, ip=ip, user_agent=user_agent, tenant_id=document.tenant_id)
    if outcome == VerificationOutcome.REVOKED_LOOKUP:
        with tenant_scope(document.tenant_id):
            emit(
                "verification.revoked_lookup",
                aggregate_type="issued_document",
                aggregate_id=document.id,
                branch_id=document.branch_id,
                payload={"number": document.number},
            )
    return {
        "issuer": document.branch.legal_name,
        "branch": document.branch.code,
        "kind": document.kind,
        "number": document.number,
        "issued_at": document.issued_at,
        "subject": document.subject,
        "status": document.status,
        "superseded_by": document.superseded_by.number if document.superseded_by else None,
        "revoked_reason": document.revoked_reason
        if document.status == DocumentStatus.REVOKED
        else None,
        "pdf_sha256": document.pdf_sha256,
        "content_hash": document.content_hash,
        "seal_level": document.seal_level,
        "transparency_leaf_index": document.transparency_leaf_index,
    }


def digest(token: str, short_code: str, *, ip: str | None, user_agent: str = "") -> dict[str, Any]:
    rate_key = f"verify:digest:{hash_ip(ip)}"
    count = cache.get(rate_key, 0) + 1
    cache.set(rate_key, count, timeout=60)
    if count > DIGEST_RATE:
        _record(
            token,
            VerificationOutcome.RATE_LIMITED,
            ip=ip,
            user_agent=user_agent,
            short_code=short_code,
        )
        raise TooManyRequests("verify.rate_limited")
    document = _find(token)
    if document is None:
        _record(
            token,
            VerificationOutcome.NOT_FOUND,
            ip=ip,
            user_agent=user_agent,
            short_code=short_code,
        )
        raise NotFound("verify.not_found", code="verify_not_found")
    if normalise_short_code(short_code) != document.short_code:
        _record(
            token,
            VerificationOutcome.DIGEST_BAD,
            ip=ip,
            user_agent=user_agent,
            tenant_id=document.tenant_id,
            short_code=short_code,
        )
        raise NotFound("verify.short_code_mismatch", code="verify_short_code_mismatch")
    _record(
        token,
        VerificationOutcome.DIGEST_OK,
        ip=ip,
        user_agent=user_agent,
        tenant_id=document.tenant_id,
        short_code=short_code,
    )
    return {
        "number": document.number,
        "kind": document.kind,
        "status": document.status,
        "digest": document.digest,
    }


def report_suspicious(
    token: str, *, reporter_name: str, reporter_contact: str, message: str, ip: str | None
) -> FraudCase:
    document = _find(token)
    if document is None:
        with platform_scope():
            case: FraudCase = FraudCase.objects.create(
                tenant_id=None,
                token=token[:32],
                reporter_name=reporter_name,
                reporter_contact=reporter_contact,
                message=message,
            )
        return case
    with tenant_scope(document.tenant_id):
        case = FraudCase.objects.create(
            document=document,
            token=token[:32],
            reporter_name=reporter_name,
            reporter_contact=reporter_contact,
            message=message,
        )
        emit(
            "fraud_case.opened",
            aggregate_type="fraud_case",
            aggregate_id=case.id,
            branch_id=document.branch_id,
            payload={"number": document.number, "reported_at": timezone.now().isoformat()},
        )
    return case
