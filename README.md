# GCP PostgreSQL → BigQuery ingest (DPDS-driven blueprint)

Blueprint-style repository for a **generic PostgreSQL → BigQuery** ingest on GCP: Terraform provisions BigQuery, GCS staging, and a Cloud Run Job; a containerized **dlt** runner reads a **Data Product Descriptor (DPDS)** JSON contract and runs **extract → transform hook → JSON Schema validation → load**.

## Use case

**Problem:** You need governed, multi-schema (or single-schema) PostgreSQL extracts into BigQuery with secrets in Secret Manager, infrastructure as code, CI/CD, and a single runtime contract.

**In scope:** Bounded parameters via `blueprint-manifest.yaml`, Apache Velocity templates (`*.vm`) for the descriptor and GitHub deploy workflow, generic SQL extraction, **developer-owned** `application/transform_hook.py`, **fail-fast** validation against the output port row contract (JSON Schema derived from **datastoreapi** `tables[0].definition.properties`), and a mandatory root checklist below. **Blindata** reserved data-product profile keys (`dpDomain`, `dpName`, `dpFqn`, `dpDisplayName`, `dpDescription`, `dpOwnerId`, `dpOwnerName`) are declared in the manifest and auto-filled into the Velocity context at instantiation (UI: "Auto-filled parameters").

### Reserved parameter keys

Use the manifest `parameters` entries with these `key` values (same names in Velocity: `${dpName}`, `${dpDomain}`, …). Do not introduce parallel custom keys for the same concepts (for example owner contact name is `${dpOwnerName}`, not a separate `contact_name`). `info.contactPoints` in the rendered descriptor uses `dpOwnerName` and `dpOwnerId` (channel `email`) so contact fields stay aligned with the catalog profile.

**Out of scope:** Business column mapping inside the blueprint (belongs in the hook), ODCS execution inside the container, creating the Terraform remote state bucket, and automatic reconciliation of input vs output schemas.

## Architecture at a glance

1. **Instantiation:** Manifest parameters (including declared reserved `dp*` keys, auto-filled by the UI) → Velocity context → rendered `descriptor/data-product-descriptor.json`, optional `infrastructure/backend.tf` (from `backend.tf.vm` if you replace the partial GCS backend), **`.github/workflows/publish.yml`** from **`publish.yml.vm`** (build/push image on version tags), and **`.github/workflows/deploy.yml`** from **`deploy.yml.vm`** (Terraform apply per environment, usually triggered externally with the published image tag). The blueprint repo ships only `*.vm` workflows so Actions stay off until a concrete product repo exists (GitHub runs `*.yml` / `*.yaml`, not `*.vm`).
2. **Runtime:** Cloud Run Job reads `DESCRIPTOR_PATH` and env (`INGEST_GCP_PROJECT_ID`, `INGEST_BQ_PARTITION_FIELD`, `INGEST_BQ_CLUSTER_FIELDS`, optional `INGEST_CURSOR_FIELD`, `INGEST_ROW_DISCRIMINATOR_COLUMN`) → `extract` (one Postgres schema per input port, row discriminator) → `transform_hook.transform_rows` → `validate_output` (JSON Schema) → `load_dlt` (BigQuery + GCS staging).

Normative references: [DPDS](https://dpds.opendatamesh.org/specifications/dpds/), [Apache Velocity](https://velocity.apache.org/engine/devel/user-guide.html), and your internal **ODM blueprint manifest** parser for `blueprint-manifest.yaml`.

## Prerequisites

- GCP project, billing, and APIs (BigQuery, Cloud Run, Artifact Registry, Secret Manager, Storage).
- **Pre-created** remote state GCS bucket (this blueprint does not create it).
- Artifact Registry repository for the runner image.
- Secret Manager secrets: PostgreSQL read-only credentials (URI or JSON) and BigQuery service account JSON for the destination.
- GitHub Actions: recommended **Workload Identity Federation** (see manifest `wif_provider` / `wif_service_account` used in `publish.yml.vm` / `deploy.yml.vm` after render). **Publish** runs on `v*.*.*` tags (or manual dispatch with `image_tag`). **Deploy** is normally triggered manually with `environment` + `image_tag`, or via `repository_dispatch` with `event_type` `deploy-ingest` and `client_payload` `{ "environment": "<one of manifest environments>", "image_tag": "v1.0.0" }`. Manifest **`environments`** drives descriptor **`internalComponents.lifecycleInfo`** keys and the Deploy workflow **choice** list.

## What instantiation does

Evaluates Velocity templates (`descriptor/data-product-descriptor.json.vm`, `infrastructure/backend.tf.vm`, `.github/workflows/publish.yml.vm`, `.github/workflows/deploy.yml.vm`) with the manifest context, including reserved **`dp*`** variables and serialized **`output_table_properties_json`** for valid JSON under each port’s `promises.api.definition.schema.tables[0].definition.properties`. Copies static scaffold files (`application/src/**`, static Terraform, `Dockerfile`, etc.). `transform_hook.py` is **not** templated and remains the extension point.

**Terraform note:** `infrastructure/backend.tf.vm` is **not** applied as HCL (`.vm` is ignored by Terraform). Either merge its contents into your root `terraform` block or rely on `versions.tf`’s partial `backend "gcs" {}` plus `terraform init -backend-config=...` as in the rendered deploy workflow.

## After you instantiate (checklist)

1. **Implement** `application/transform_hook.py` so rows match the output port **datastoreapi** column contract (see `application/README.md`).
2. **Verify** Secret Manager secrets and Terraform secret ids; confirm read-only DB access.
3. **Review** rendered `data-product-descriptor.json`: one **input port** per **`input_schemas`** entry (`promises.api.definition.schema` uses **`databaseSchemaName`** + **`tables`** only); output port the same shape (BigQuery dataset id in **`databaseSchemaName`**); **`lifecycleInfo`** keys match **`environments`**. Confirm Terraform passes partition/cluster/cursor/discriminator into the job env vars.
4. **Run** **Publish** (tag or manual dispatch) then **Deploy** per environment with the same `image_tag`, or local `terraform apply`; resolve drift between Terraform and the descriptor.
5. **Schedule** the Cloud Run Job (Scheduler or manual) and monitor logs, BigQuery row counts, and validation failures.
6. **Optional quality:** Point ODCS / Soda / dbt at the published table or contract files.
7. **Runbooks:** Document how to bump `output_port_version` / data product version on breaking contract changes.

## Where to change what

| Area | Responsibility |
| --- | --- |
| `descriptor/data-product-descriptor.json.vm` (rendered → `.json` at instantiation) | Port contract: **datastoreapi** `definition.schema` (`databaseSchemaName`, `tables[]` + column `properties`); multiple input ports when **`input_schemas`** has multiple entries |
| `application/transform_hook.py` | Column mapping and business rules |
| `infrastructure/*.tf` | GCP resources, job, IAM, secrets wiring |
| `blueprint-manifest.yaml` | Bounded parameters and `protectedResources` policy |

## Support

Fork or adapt this blueprint for your platform; open issues in your internal tracker as appropriate.
