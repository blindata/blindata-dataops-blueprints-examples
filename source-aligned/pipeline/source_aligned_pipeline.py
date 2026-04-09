# Protected: core pipeline skeleton — extend sources and destination for your domain.
"""Source-aligned dlt skeleton: load operational data into a curated dataset.

Replace `main_entity` with real sources (files in raw S3, databases, APIs). Switch
`destination` from duckdb (local smoke test) to filesystem/S3, Athena, or your
warehouse when deploying.
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterator

import dlt

try:
    from pipeline.settings import DOMAIN_SLUG, ENABLE_PII_MASKING
except ImportError:
    # Before Velocity renders `settings.py` from `settings.py.vm`, use dev defaults.
    ENABLE_PII_MASKING = True
    DOMAIN_SLUG = "local"


def _apply_pii(value: str | None) -> str | None:
    if value is None:
        return None
    if ENABLE_PII_MASKING:
        return hashlib.sha256(value.encode()).hexdigest()
    return value


@dlt.resource(table_name="main_entity", write_disposition="replace")
def main_entity() -> Iterator[dict[str, Any]]:
    """Replace with loads from your operational system."""
    yield {
        "entity_id": "example-1",
        "sensitive_field": _apply_pii("user@example.com"),
        "updated_at": "2024-01-01T00:00:00Z",
    }


def run() -> None:
    pipeline = dlt.pipeline(
        pipeline_name=f"source_aligned_{DOMAIN_SLUG}",
        destination="duckdb",
        dataset_name="curated",
    )
    pipeline.run(main_entity())


if __name__ == "__main__":
    run()
