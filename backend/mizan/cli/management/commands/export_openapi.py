"""Write the OpenAPI document of the API (consumed by the generated TypeScript client)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "Export the OpenAPI 3.1 document to a file (or stdout with '-')."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("path", nargs="?", default="-")
        parser.add_argument("--indent", type=int, default=2)

    def handle(self, *args: Any, **options: Any) -> None:
        from mizan.config.api import api

        schema = api.get_openapi_schema(path_prefix="")
        text = json.dumps(schema, indent=options["indent"], ensure_ascii=False, default=str)
        path = str(options["path"])
        if path == "-":
            self.stdout.write(text)
            return
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
        self.stdout.write(f"wrote {target} ({len(schema.get('paths', {}))} paths)")
