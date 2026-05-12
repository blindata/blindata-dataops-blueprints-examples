# Product-side extension: map extracted rows to the output port row shape (post-instantiation).
# Purpose: keep all business rules out of the generic runner; swap implementation per data product.
from __future__ import annotations

import os
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.descriptor_loader import InputIngestConfig, OutputIngestConfig


def transform_rows(
    rows: Iterable[dict],
    *,
    input_configs: tuple["InputIngestConfig", ...],
    output_config: "OutputIngestConfig",
) -> Iterable[dict]:
    """Map raw extracted rows to the output port row contract (JSON Schema from datastoreapi).

    Implement this after instantiation. For local smoke tests only, set
    TRANSFORM_HOOK_IDENTITY=1 to pass rows through unchanged (rows must
    already satisfy output_config.physical_schema).
    """
    _ = (input_configs, output_config)
    if os.environ.get("TRANSFORM_HOOK_IDENTITY") == "1":
        yield from rows
        return
    raise NotImplementedError(
        "Implement transform_rows in transform_hook.py to map source rows to the "
        "descriptor output port datastore-derived schema. For dry runs with matching "
        "schemas, set TRANSFORM_HOOK_IDENTITY=1."
    )
