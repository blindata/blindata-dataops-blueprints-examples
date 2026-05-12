# Loads and parses data-product-descriptor.json (DPDS) and exposes typed input/output settings
# derived from datastoreapi promises. Purpose: one place for contract parsing used by extract,
# validate, and load steps.
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class InputIngestConfig:
    """PostgreSQL extract settings from one input port (single databaseSchemaName + source table)."""

    connection_secret_env: str
    port_key: str
    database_schema_name: str
    source_table: str
    cursor_field: str | None
    row_discriminator_column: str


@dataclass(frozen=True)
class OutputIngestConfig:
    """BigQuery load target and row contract derived from output port datastoreapi table."""

    project_id: str
    dataset_id: str
    table_id: str
    credentials_secret_env: str
    partition_field: str
    cluster_fields: tuple[str, ...]
    physical_schema: Mapping[str, Any]


class DescriptorError(ValueError):
    pass


PG_SECRET_ENV = "SOURCES__POSTGRES__CREDENTIALS"
BQ_SECRET_ENV = "DESTINATION__BIGQUERY__CREDENTIALS"


def _require_mapping(obj: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(obj, Mapping):
        raise DescriptorError(f"{path} must be an object")
    return obj


def _require_env(name: str) -> str:
    raw = os.environ.get(name, "").strip()
    if not raw:
        raise DescriptorError(
            f"Environment variable {name} is required (injected by Terraform / Cloud Run for runtime)"
        )
    return raw


def _optional_env(name: str) -> str | None:
    raw = os.environ.get(name, "").strip()
    return raw or None


def _cluster_fields_from_env() -> tuple[str, ...]:
    raw = _require_env("INGEST_BQ_CLUSTER_FIELDS")
    parts = tuple(p.strip() for p in raw.split(",") if p.strip())
    if not parts:
        raise DescriptorError("INGEST_BQ_CLUSTER_FIELDS must list at least one column (comma-separated)")
    return parts


def _prop_to_json_schema_fragment(spec: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = str(spec.get("physicalType") or "string")
    ptype = raw.lower()
    base = ptype.split("(")[0].strip()
    nullable = bool(spec.get("isNullable", True))
    core: dict[str, Any]
    if base in ("boolean", "bool"):
        core = {"type": "boolean"}
    elif "timestamp" in ptype:
        core = {"type": "string", "format": "date-time"}
    elif "decimal" in ptype or "double" in ptype or "numeric" in ptype or "float" in ptype:
        core = {"type": "number"}
    elif base in ("int", "integer", "bigint", "smallint", "serial") or (
        "int" in ptype and "decimal" not in ptype and "point" not in ptype
    ):
        core = {"type": "integer"}
    elif re.search(r"\bdate\b", ptype) and "timestamp" not in ptype:
        core = {"type": "string", "format": "date"}
    else:
        core = {"type": "string"}
    if nullable:
        return {"anyOf": [{"type": "null"}, core]}
    return core


def datastore_properties_to_json_schema(properties: Mapping[str, Any]) -> dict[str, Any]:
    """Build a Draft 2020-12 style object schema from datastoreapi column definitions."""
    prop_schema: dict[str, Any] = {}
    required: list[str] = []
    for name, spec in properties.items():
        if not isinstance(spec, Mapping):
            continue
        prop_schema[name] = _prop_to_json_schema_fragment(spec)
        if spec.get("isNullable") is False:
            required.append(str(name))
    out: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": prop_schema,
        "additionalProperties": True,
    }
    if required:
        out["required"] = sorted(required)
    return out


def _api_definition(port: Mapping[str, Any], path: str) -> Mapping[str, Any]:
    promises = _require_mapping(port.get("promises"), f"{path}.promises")
    api = _require_mapping(promises.get("api"), f"{path}.promises.api")
    if api.get("specification") != "datastoreapi":
        raise DescriptorError(f"{path}.promises.api.specification must be 'datastoreapi'")
    return _require_mapping(api.get("definition"), f"{path}.promises.api.definition")


def _parse_input_port(input_port: Mapping[str, Any], index: int) -> InputIngestConfig:
    path = f"inputPorts[{index}]"
    definition = _api_definition(input_port, path)
    schema = _require_mapping(definition.get("schema"), f"{path}.promises.api.definition.schema")

    db_schema = str(schema.get("databaseSchemaName") or "").strip()
    if not db_schema:
        raise DescriptorError(f"{path}.promises.api.definition.schema.databaseSchemaName is required")

    tables = schema.get("tables")
    if not isinstance(tables, list) or not tables:
        raise DescriptorError(f"{path}.promises.api.definition.schema.tables must be a non-empty array")
    table0 = _require_mapping(tables[0], f"{path}.promises.api.definition.schema.tables[0]")
    source_table = str(table0.get("name") or "").strip()
    if not source_table:
        raise DescriptorError(f"{path}.promises.api.definition.schema.tables[0].name is required")

    port_key = str(input_port.get("name") or "").strip()
    if not port_key:
        raise DescriptorError(f"{path}.name is required")

    cursor = _optional_env("INGEST_CURSOR_FIELD")
    discriminator = _require_env("INGEST_ROW_DISCRIMINATOR_COLUMN")

    return InputIngestConfig(
        connection_secret_env=PG_SECRET_ENV,
        port_key=port_key,
        database_schema_name=db_schema,
        source_table=source_table,
        cursor_field=cursor,
        row_discriminator_column=discriminator,
    )


def _parse_output_port(output_port: Mapping[str, Any]) -> OutputIngestConfig:
    path = "outputPorts[0]"
    definition = _api_definition(output_port, path)
    schema = _require_mapping(definition.get("schema"), f"{path}.promises.api.definition.schema")

    dataset_id = str(schema.get("databaseSchemaName") or "").strip()
    if not dataset_id:
        raise DescriptorError(f"{path}.promises.api.definition.schema.databaseSchemaName is required")

    tables = schema.get("tables")
    if not isinstance(tables, list) or not tables:
        raise DescriptorError(f"{path}.promises.api.definition.schema.tables must be a non-empty array")
    table0 = _require_mapping(tables[0], f"{path}.promises.api.definition.schema.tables[0]")
    table_id = str(table0.get("name") or "").strip()
    if not table_id:
        raise DescriptorError(f"{path}.promises.api.definition.schema.tables[0].name is required")

    tdef = _require_mapping(table0.get("definition"), f"{path}.promises.api.definition.schema.tables[0].definition")
    props = tdef.get("properties")
    if not isinstance(props, Mapping):
        raise DescriptorError(
            f"{path}.promises.api.definition.schema.tables[0].definition.properties must be an object"
        )
    physical_schema = datastore_properties_to_json_schema(props)

    project_id = _require_env("INGEST_GCP_PROJECT_ID")
    partition_field = _require_env("INGEST_BQ_PARTITION_FIELD")
    cluster_fields = _cluster_fields_from_env()

    return OutputIngestConfig(
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=table_id,
        credentials_secret_env=BQ_SECRET_ENV,
        partition_field=partition_field,
        cluster_fields=cluster_fields,
        physical_schema=physical_schema,
    )


def load_descriptor(path: str | None = None) -> tuple[tuple[InputIngestConfig, ...], OutputIngestConfig]:
    descriptor_path = path or os.environ.get("DESCRIPTOR_PATH", "/app/descriptor/data-product-descriptor.json")
    raw = Path(descriptor_path).read_text(encoding="utf-8")
    doc = json.loads(raw)
    root = _require_mapping(doc, "descriptor document")

    interface = _require_mapping(root.get("interfaceComponents"), "interfaceComponents")
    inputs = interface.get("inputPorts")
    outputs = interface.get("outputPorts")
    if not isinstance(inputs, list) or not inputs:
        raise DescriptorError("interfaceComponents.inputPorts must be a non-empty array")
    if not isinstance(outputs, list) or not outputs:
        raise DescriptorError("interfaceComponents.outputPorts must be a non-empty array")

    input_cfgs = tuple(
        _parse_input_port(_require_mapping(p, f"inputPorts[{i}]"), i) for i, p in enumerate(inputs)
    )
    output_port = _require_mapping(outputs[0], "outputPorts[0]")

    return input_cfgs, _parse_output_port(output_port)
