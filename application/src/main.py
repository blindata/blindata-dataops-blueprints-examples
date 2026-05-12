# CLI entrypoint for the Cloud Run ingest job: load DPDS descriptor, extract, transform hook,
# validate rows, load to BigQuery. Purpose: single orchestrated pipeline for `python -m src.main`.
from __future__ import annotations

import logging
import sys
from itertools import chain
from pathlib import Path

app_root = Path(__file__).resolve().parent.parent
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))

import transform_hook  # noqa: E402  pylint: disable=import-error

from .descriptor_loader import load_descriptor  # noqa: E402
from .extract import extract_rows  # noqa: E402
from .load_dlt import load_to_bigquery  # noqa: E402
from .validate_output import (  # noqa: E402
    build_validator,
    validate_rows,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    input_cfgs, output_cfg = load_descriptor()
    validator = build_validator(output_cfg)

    raw_rows = chain.from_iterable(extract_rows(c) for c in input_cfgs)
    transformed = transform_hook.transform_rows(
        raw_rows,
        input_configs=input_cfgs,
        output_config=output_cfg,
    )
    validated = validate_rows(
        transformed,
        output_cfg=output_cfg,
        validator=validator,
    )
    logger.info("Validated %s rows", len(validated))
    load_to_bigquery(validated, output_cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
