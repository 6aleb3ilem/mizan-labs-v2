"""Structured logging: request id, tenant and actor on every record; JSON in the cloud."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from mizan.platform import context


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        req = context.request_context()
        tenant = context.current_tenant_id.get()
        actor = context.actor()
        record.request_id = req.request_id or "-"
        record.tenant_id = str(tenant) if tenant else "-"
        record.actor_id = str(actor.id) if actor.id else actor.type.lower()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "tenant_id": getattr(record, "tenant_id", "-"),
            "actor_id": getattr(record, "actor_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("event", "duration_ms", "status", "path", "task"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)
