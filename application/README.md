# Ingest runner application

Python entrypoint (`python -m src.main`) loads `DESCRIPTOR_PATH` (default `/app/descriptor/data-product-descriptor.json`). That JSON file is **not** committed in the blueprint: it is rendered from `descriptor/data-product-descriptor.json.vm` at instantiation and baked or mounted for the job image. The runner then performs generic PostgreSQL extraction (one schema per **input port**), calls your **`transform_hook.py`**, validates each row against the output port **JSON Schema**, then loads with **dlt** to BigQuery using GCS staging (`INGEST_GCS_STAGING`).

## `transform_hook.py`

Implement:

```python
def transform_rows(rows, *, input_configs, output_config):
    ...
```

- `input_configs` is a `tuple` of `InputIngestConfig` (one per `interfaceComponents.inputPorts[]` entry). Each port’s `promises.api.definition.schema` declares only **`databaseSchemaName`** and **`tables`** (datastoreapi).
- `output_config` is `OutputIngestConfig` from the first output port; BigQuery **project** and partition/cluster metadata come from **`INGEST_*`** env vars (set by Terraform), not from extra keys under `tables[0].definition`.
- Return an **iterable of dicts** matching `output_config.physical_schema` (JSON Schema derived from the output table `definition.properties` in the descriptor).

**Local / smoke:** if rows already satisfy the contract, set `TRANSFORM_HOOK_IDENTITY=1` to pass rows through. Production jobs should implement real mapping. For local runs without Terraform, set the **`INGEST_*`** variables yourself to match your descriptor and target table.

## Runtime environment

| Variable | Purpose |
| --- | --- |
| `DESCRIPTOR_PATH` | Path to DPDS JSON |
| `SOURCES__POSTGRES__CREDENTIALS` | File path or inline secret for Postgres |
| `DESTINATION__BIGQUERY__CREDENTIALS` | File path to BigQuery SA JSON |
| `INGEST_GCS_STAGING` | `gs://` bucket URL for dlt staging (set by Terraform on the job) |
| `INGEST_GCP_PROJECT_ID` | GCP project for BigQuery loads (Terraform) |
| `INGEST_BQ_PARTITION_FIELD` | Target table partition column name (Terraform; not in descriptor `properties`) |
| `INGEST_BQ_CLUSTER_FIELDS` | Comma-separated clustering column names (Terraform) |
| `INGEST_CURSOR_FIELD` | Optional Postgres incremental cursor column (Terraform; empty for full snapshots) |
| `INGEST_ROW_DISCRIMINATOR_COLUMN` | Injected column name for source schema (Terraform) |
| `CURSOR_STATE_PATH` | Optional JSON file for incremental cursor watermarks (ephemeral unless you mount storage) |
| `TRANSFORM_HOOK_IDENTITY` | Set to `1` only for identity smoke tests |

## Velocity context keys

**Blindata reserved keys (declared in `blueprint-manifest.yaml` with `key` = `dpDomain`, `dpName`, …; auto-filled in the UI under "Auto-filled parameters"):**

| Key | Typical use in templates |
| --- | --- |
| `dpDomain` | `info.domain`, naming |
| `dpName` | `info.name`; pass as Terraform `-var=data_product_name=…` (same machine id) |
| `dpFqn` | `info.fullyQualifiedName` and port `fullyQualifiedName` prefixes |
| `dpDisplayName` | `info.displayName` (falls back to `dpName` in the descriptor template) |
| `dpDescription` | `info.description` |
| `dpOwnerId` | `info.owner.id` |
| `dpOwnerName` | `info.contactPoints[].name` |

**Other manifest parameters** use the same `key` as the Velocity variable (for example `input_schemas`, `input_port_name_prefix`, `gcp_project_id`). The template emits **one input port per** `input_schemas[]` value. For the BigQuery column map, the orchestrator injects **`output_table_properties_json`** (unquoted object literal) into `tables[0].definition.properties`. The **`dependsOn`** manifest string is copied onto each input port for catalog use only.

## Contract changes

When you change the hook output shape, update the manifest `output_table_properties`, re-render the descriptor, bump **`output_port_version`** (and optionally the data product `info.version`), and coordinate consumers.
