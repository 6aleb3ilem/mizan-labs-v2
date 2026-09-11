"""Append-only Merkle log of issued documents (SPEC §18.8), RFC 6962 hashing, per tenant."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from django.db import connection, transaction
from django.utils import timezone

from mizan.apps.documents.models import (
    IssuedDocument,
    SigningKey,
    TransparencyHead,
    TransparencyLeaf,
)
from mizan.platform import context


def _sha(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def leaf_data(document: IssuedDocument) -> bytes:
    return (
        document.id.bytes
        + bytes.fromhex(document.content_hash)
        + document.issued_at.isoformat().encode()
    )


def leaf_hash(document: IssuedDocument) -> bytes:
    return _sha(b"\x00" + leaf_data(document))


def merkle_root(leaves: list[bytes]) -> bytes:
    if not leaves:
        return _sha(b"")
    if len(leaves) == 1:
        return leaves[0]
    k = 1
    while k * 2 < len(leaves):
        k *= 2
    return _sha(b"\x01" + merkle_root(leaves[:k]) + merkle_root(leaves[k:]))


def inclusion_proof(leaves: list[bytes], index: int) -> list[bytes]:
    """RFC 6962 audit path for ``leaves[index]``."""
    if len(leaves) <= 1:
        return []
    k = 1
    while k * 2 < len(leaves):
        k *= 2
    if index < k:
        return [*inclusion_proof(leaves[:k], index), merkle_root(leaves[k:])]
    return [*inclusion_proof(leaves[k:], index - k), merkle_root(leaves[:k])]


def verify_inclusion(leaf: bytes, index: int, size: int, proof: list[bytes], root: bytes) -> bool:
    if index >= size:
        return False
    node = leaf
    f_n, s_n = index, size - 1
    for sibling in proof:
        if f_n % 2 == 1 or f_n == s_n:
            node = _sha(b"\x01" + sibling + node)
            while f_n % 2 == 0 and f_n != 0:
                f_n //= 2
                s_n //= 2
        else:
            node = _sha(b"\x01" + node + sibling)
        f_n //= 2
        s_n //= 2
    return node == root


def _lock_tenant_log() -> None:
    tenant_id = context.require_tenant_id()
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [f"transparency:{tenant_id}"])


def append_leaf(document: IssuedDocument) -> TransparencyLeaf:
    with transaction.atomic():
        _lock_tenant_log()
        existing = list(
            TransparencyLeaf.objects.order_by("index").values_list("leaf_hash", flat=True)
        )
        new_hash = leaf_hash(document)
        hashes = [bytes.fromhex(h) for h in existing] + [new_hash]
        root = merkle_root(hashes)
        leaf: TransparencyLeaf = TransparencyLeaf.objects.create(
            index=len(existing),
            document=document,
            leaf_hash=new_hash.hex(),
            tree_head_hash=root.hex(),
        )
        IssuedDocument.all_objects.filter(pk=document.pk).update(transparency_leaf_index=leaf.index)
        document.transparency_leaf_index = leaf.index
    return leaf


def current_root() -> tuple[int, str]:
    hashes = [
        bytes.fromhex(h)
        for h in TransparencyLeaf.objects.order_by("index").values_list("leaf_hash", flat=True)
    ]
    return len(hashes), merkle_root(hashes).hex()


def proof_for(index: int) -> dict[str, Any]:
    hashes = [
        bytes.fromhex(h)
        for h in TransparencyLeaf.objects.order_by("index").values_list("leaf_hash", flat=True)
    ]
    if index < 0 or index >= len(hashes):
        raise IndexError(index)
    return {
        "index": index,
        "tree_size": len(hashes),
        "leaf_hash": hashes[index].hex(),
        "root_hash": merkle_root(hashes).hex(),
        "proof": [p.hex() for p in inclusion_proof(hashes, index)],
    }


def publish_head(key: SigningKey) -> TransparencyHead:
    """Sign the current tree head with a QR key (published daily on the verification site)."""
    from mizan.apps.documents.keys import load_qr_private_key
    from mizan.apps.documents.qr import sign_payload

    size, root = current_root()
    published_at = timezone.now()
    payload = {"size": size, "root": root, "published_at": published_at.isoformat(), "kid": key.kid}
    signature = sign_payload(payload, load_qr_private_key(key), key.kid)
    head: TransparencyHead = TransparencyHead.objects.create(
        tree_size=size, root_hash=root, signature=signature, key=key, published_at=published_at
    )
    TransparencyLeaf.objects.filter(published_at__isnull=True).update(published_at=published_at)
    return head


def head_payload(head: TransparencyHead) -> dict[str, Any]:
    return {
        "tree_size": head.tree_size,
        "root_hash": head.root_hash,
        "published_at": head.published_at.isoformat(),
        "kid": head.key.kid,
        "signature": head.signature,
        "canonical": json.dumps(
            {"size": head.tree_size, "root": head.root_hash}, separators=(",", ":")
        ),
    }
