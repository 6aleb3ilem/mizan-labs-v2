import uuid

import pytest

from mizan.platform.auth.jwt import InvalidToken, decode_access_token, issue_access_token


def _issue(**overrides: object) -> str:
    kwargs: dict[str, object] = {
        "user_id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "realm": "STAFF",
        "session_id": uuid.uuid4(),
    }
    kwargs.update(overrides)
    return issue_access_token(**kwargs)  # type: ignore[arg-type]


def test_round_trip() -> None:
    user_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    token = _issue(user_id=user_id, tenant_id=tenant_id, now=1_000_000)
    claims = decode_access_token(token, now=1_000_100)
    assert claims.user_id == user_id
    assert claims.tenant_id == tenant_id
    assert claims.realm == "STAFF"
    assert claims.expires_at == 1_000_000 + 900


def test_expired_token_is_rejected() -> None:
    token = _issue(now=1_000_000)
    with pytest.raises(InvalidToken):
        decode_access_token(token, now=1_000_000 + 901)


def test_tampered_token_is_rejected() -> None:
    token = _issue()
    header, payload, signature = token.split(".")
    with pytest.raises(InvalidToken):
        decode_access_token(f"{header}.{payload}.{signature[:-2]}xx")
    with pytest.raises(InvalidToken):
        decode_access_token("not-a-token")


def test_platform_operator_token_has_no_tenant() -> None:
    token = _issue(tenant_id=None, realm="PLATFORM")
    assert decode_access_token(token).tenant_id is None
