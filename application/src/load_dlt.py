# dlt pipeline: append validated rows to the BigQuery table declared in the output port contract.
# Purpose: isolate destination I/O and credentials env wiring from extract/transform logic.
from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import dlt
from dlt.destinations import bigquery

from .descriptor_loader import OutputIngestConfig

logger = logging.getLogger(__name__)


def _credentials_file(env_name: str) -> str:
    raw = os.environ.get(env_name)
    if not raw:
        raise RuntimeError(f"Missing environment variable {env_name}")
    path = Path(raw)
    if not path.is_file():
        raise RuntimeError(f"{env_name} must point to a readable file, got {raw}")
    resolved = str(path.resolve())
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", resolved)
    return resolved


def load_to_bigquery(rows: Iterable[dict[str, Any]], output_cfg: OutputIngestConfig) -> None:
    staging = os.environ.get("INGEST_GCS_STAGING")
    if not staging:
        raise RuntimeError("INGEST_GCS_STAGING must be set to a gs:// bucket URL for dlt staging")

    _credentials_file(output_cfg.credentials_secret_env)

    destination = bigquery(bucket_url=staging)

    pipeline = dlt.pipeline(
        pipeline_name=f"{output_cfg.dataset_id}_{output_cfg.table_id}_ingest",
        destination=destination,
        dataset_name=output_cfg.dataset_id,
    )

    row_list = list(rows)

    @dlt.resource(
        name=output_cfg.table_id,
        write_disposition="replace",
    )
    def contract_table() -> Iterable[dict[str, Any]]:
        yield from row_list

    load_info = pipeline.run(contract_table(), loader_file_format="parquet")
    logger.info("dlt load completed: %s", load_info)
