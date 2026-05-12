# Read-only PostgreSQL extraction over authorized schemas, row discriminator, optional cursor.
# Purpose: generic SQL pull driven by descriptor input port settings (no business mapping here).
from __future__ import annotations

import json
import os
import re
import tempfile
from urllib.parse import quote_plus
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .descriptor_loader import InputIngestConfig

_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


def _resolve_secret_value(env_name: str) -> str:
    raw = os.environ.get(env_name)
    if not raw:
        raise RuntimeError(f"Missing environment variable {env_name}")
    path = Path(raw)
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return raw.strip()


def _build_sqlalchemy_url(secret_payload: str) -> str:
    if secret_payload.startswith("postgresql://") or secret_payload.startswith("postgres://"):
        return secret_payload
    data = json.loads(secret_payload)
    host = data["host"]
    port = int(data.get("port", 5432))
    user = data["user"]
    password = data["password"]
    dbname = data["database"]
    return (
        "postgresql+psycopg2://"
        f"{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{quote_plus(dbname)}"
    )


def _engine_for_input(input_cfg: InputIngestConfig) -> Engine:
    secret = _resolve_secret_value(input_cfg.connection_secret_env)
    url = _build_sqlalchemy_url(secret)
    return create_engine(url, pool_pre_ping=True)


def _validate_ident(name: str, label: str) -> str:
    if not _IDENT.match(name):
        raise ValueError(f"Invalid {label} identifier: {name!r}")
    return name


def _cursor_state_path() -> Path:
    return Path(os.environ.get("CURSOR_STATE_PATH", "/tmp/ingest_cursor_state.json"))


def _load_cursor_state(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
        return data
    return {}


def _persist_cursor_state(path: Path, state: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(state, sort_keys=True))
        Path(tmp_name).replace(path)
    except OSError:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def extract_rows(input_cfg: InputIngestConfig) -> Iterator[dict[str, Any]]:
    engine = _engine_for_input(input_cfg)
    table = _validate_ident(input_cfg.source_table, "table")
    discriminator = _validate_ident(input_cfg.row_discriminator_column, "rowDiscriminatorColumn")
    cursor_field = input_cfg.cursor_field
    if cursor_field:
        _validate_ident(cursor_field, "cursorField")

    state_path = _cursor_state_path()
    cursor_state = _load_cursor_state(state_path)

    try:
        schema_sql = _validate_ident(input_cfg.database_schema_name, "schema")
        qualified = f'"{schema_sql}"."{table}"'

        if cursor_field:
            watermark = cursor_state.get(f"{input_cfg.port_key}:{schema_sql}:{cursor_field}")
            if watermark:
                clause = f'"{cursor_field}" > :wm'
                params: dict[str, Any] = {"wm": watermark}
            else:
                clause = "true"
                params = {}
            stmt = text(f"SELECT * FROM {qualified} WHERE {clause}")
        else:
            stmt = text(f"SELECT * FROM {qualified}")
            params = {}

        with engine.connect() as conn:
            result = conn.execution_options(stream_results=True).execute(stmt, params)
            keys = list(result.keys())
            for row in result.mappings():
                payload = {k: row[k] for k in keys}
                payload[discriminator] = schema_sql
                yield dict(payload)

                if cursor_field and row[cursor_field] is not None:
                    key = f"{input_cfg.port_key}:{schema_sql}:{cursor_field}"
                    current = cursor_state.get(key)
                    serialized = row[cursor_field]
                    if hasattr(serialized, "isoformat"):
                        serialized = serialized.isoformat()
                    serialized_str = str(serialized)
                    if current is None or serialized_str > current:
                        cursor_state[key] = serialized_str
    finally:
        engine.dispose()
        if cursor_field:
            _persist_cursor_state(state_path, cursor_state)
