"""Object storage: local files in development, S3-compatible (MinIO, Cloudflare R2) elsewhere."""

from __future__ import annotations

import hashlib
import re
from functools import cache
from pathlib import Path
from typing import Any, Protocol

from django.conf import settings

_SAFE_KEY = re.compile(r"^[A-Za-z0-9._/-]{1,512}$")


class StorageError(Exception):
    pass


def validate_key(key: str) -> str:
    if not _SAFE_KEY.match(key) or ".." in key or key.startswith("/"):
        raise StorageError(f"invalid object key {key!r}")
    return key


class ObjectStorage(Protocol):
    def put(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...


class LocalStorage:
    """Files under ``MIZAN_STORAGE_LOCAL_ROOT/<bucket>/<key>``."""

    def __init__(self, root: Path, bucket: str) -> None:
        self.root = Path(root) / bucket

    def _path(self, key: str) -> Path:
        return self.root / validate_key(key)

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise StorageError(f"object not found: {key}")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()


class S3Storage:
    def __init__(
        self,
        bucket: str,
        *,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
        region: str,
    ) -> None:
        import boto3

        self.bucket = bucket
        self.client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        self.client.put_object(
            Bucket=self.bucket, Key=validate_key(key), Body=data, ContentType=content_type
        )

    def get(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=validate_key(key))
        except self.client.exceptions.NoSuchKey as exc:
            raise StorageError(f"object not found: {key}") from exc
        return bytes(response["Body"].read())

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=validate_key(key))
        except Exception:
            return False
        return True

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=validate_key(key))


def _build(bucket: str) -> ObjectStorage:
    env = settings.ENV
    if settings.MIZAN_STORAGE_BACKEND == "s3":
        return S3Storage(
            bucket,
            endpoint_url=env.s3_endpoint_url,
            access_key=env.s3_access_key_id,
            secret_key=env.s3_secret_access_key,
            region=env.s3_region,
        )
    return LocalStorage(settings.MIZAN_STORAGE_LOCAL_ROOT, bucket)


@cache
def documents_storage() -> ObjectStorage:
    return _build(settings.ENV.s3_bucket_documents)


@cache
def attachments_storage() -> ObjectStorage:
    return _build(settings.ENV.s3_bucket_attachments)


def content_key(prefix: str, data: bytes, suffix: str) -> str:
    """Immutable key derived from the content hash (SPEC §18.1)."""
    digest = hashlib.sha256(data).hexdigest()
    return f"{prefix}/{digest[:2]}/{digest}{suffix}"
