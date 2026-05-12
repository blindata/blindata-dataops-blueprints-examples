# Fail-fast JSON Schema validation (Draft 2020-12) for each transformed row vs output contract.
# Purpose: enforce datastore-derived physical schema before BigQuery load.
from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .descriptor_loader import OutputIngestConfig

logger = logging.getLogger(__name__)


def build_validator(output_cfg: OutputIngestConfig) -> Draft202012Validator:
    schema = dict(output_cfg.physical_schema)
    return Draft202012Validator(schema)


def validate_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    output_cfg: OutputIngestConfig,
    validator: Draft202012Validator | None = None,
) -> list[dict[str, Any]]:
    v = validator or build_validator(output_cfg)
    validated: list[dict[str, Any]] = []
    for row in rows:
        try:
            v.validate(row)
        except ValidationError as exc:
            sample_keys = sorted(row.keys())
            logger.error("Row failed JSON Schema validation keys=%s error=%s", sample_keys, exc.message)
            raise SystemExit(1) from exc
        validated.append(dict(row))
    return validated
