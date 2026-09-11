"""Typed environment for the platform (pydantic-settings).

Every value has a safe development default. Production values come from the environment
(Secret Manager → Cloud Run env). Nothing business-related lives here: business values are
configuration in the database (SPEC §4, Appendix W).
"""

from __future__ import annotations

from functools import cached_property
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Env(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mizan_env: Literal["dev", "test", "staging", "production"] = "dev"
    secret_key: str = "dev-only-change-me"
    debug: bool = False

    database_url: str = "postgresql://mizan:mizan@127.0.0.1:5432/mizan"
    conn_max_age: int = 60
    allowed_hosts: str = "localhost,127.0.0.1"
    cors_allowed_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176"
    )

    # Object storage: local files in dev, S3-compatible (MinIO, Cloudflare R2) elsewhere.
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_root: str = "var/storage"
    s3_endpoint_url: str | None = None
    s3_region: str = "auto"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket_documents: str = "mizan-documents"
    s3_bucket_attachments: str = "mizan-attachments"

    # E-mail (Mailpit in dev)
    email_backend: str | None = None
    email_host: str = "127.0.0.1"
    email_port: int = 1025
    email_use_tls: bool = False
    email_host_user: str = ""
    email_host_password: str = ""
    email_from: str = "Mizan Labs <no-reply@mizanlabs.local>"

    # Document signing: local PEM keys in dev, cloud KMS handles elsewhere.
    signing_backend: Literal["local", "kms"] = "local"
    signing_local_dir: str = "var/keys"
    tsa_url: str | None = None

    # Public origins used inside documents, messages and CORS.
    verify_base_url: str = "http://localhost:5176"
    portal_base_url: str = "http://localhost:5175"
    app_base_url: str = "http://localhost:5173"
    admin_base_url: str = "http://localhost:5174"

    # Session tokens for the single-page applications.
    jwt_issuer: str = "mizan"
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_seconds: int = 30 * 24 * 3600

    log_json: bool = False
    log_level: str = "INFO"

    @cached_property
    def allowed_hosts_list(self) -> list[str]:
        return _csv(self.allowed_hosts)

    @cached_property
    def cors_origins_list(self) -> list[str]:
        return _csv(self.cors_allowed_origins)

    @property
    def is_production_like(self) -> bool:
        return self.mizan_env in ("staging", "production")


env = Env()
