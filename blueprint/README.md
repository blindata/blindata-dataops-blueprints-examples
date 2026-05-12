# Blueprint: PostgreSQL → BigQuery ingest (DPDS-driven)

## What this blueprint is about

The blueprint defines a **governed ingest** on **Google Cloud**: read-only **PostgreSQL** extracts (one or more schemas, same logical table) flow through a containerized runner into **BigQuery**, with **GCS** staging, **Secret Manager** credentials, **Terraform** infrastructure, and **GitHub Actions** for build and deploy.

The **Python** application implements a fixed pipeline (extract → your transform hook → JSON Schema validation → **dlt** load); **business column mapping** belongs in `**application/transform_hook.py`** after instantiation.

## Data product use case

**Problem:** You need a repeatable pattern to land PostgreSQL data into BigQuery under a **single output contract**, with infrastructure and delivery aligned to **environments** (for example `dev`, `prod`).

**What the instantiated product owns:** Implement `**transform_hook.py`**, curate **Secret Manager** values, run **Publish** then **Deploy** per environment, and operate the **Cloud Run Job** (schedule, monitoring). The blueprint supplies the generic extract, validation, load path, Terraform modules, Docker image, and templated descriptor and workflows.

**Out of scope for the blueprint itself:** Detailed business rules inside the generic modules (those live in the hook), provisioning the remote Terraform state bucket, and automatic reconciliation of every possible source column to the output without your hook logic.

## Data product instantiation

**Velocity templates** (`.vm` files) in this blueprint are the parameterized sources. They are:


| Template                                     | Typical output in the data product repository |
| -------------------------------------------- | --------------------------------------------- |
| `descriptor/data-product-descriptor.json.vm` | `descriptor/data-product-descriptor.json`     |
| `.github/workflows/publish.yml.vm`           | `.github/workflows/publish.yml`               |
| `.github/workflows/deploy.yml.vm`            | `.github/workflows/deploy.yml`                |
| `README.md.vm`                               | `README.md` at the repository root            |
| `infrastructure/backend.tf.vm`               | `infrastructure/backend.tf`                   |


**When the data product repository is instantiated**, the orchestrator builds a Velocity context, evaluates each `.vm` file above and writes the corresponding rendered artifacts. Every **non-template** file from the blueprint—`application/` (including `application/transform_hook.py`), static `infrastructure/*.tf`, `Dockerfile`, `blueprint-manifest.yaml`, and the rest of the scaffold—is **copied unchanged** into the new repo so it is a complete project. 

## Data product publication

**Publish** (rendered `.github/workflows/publish.yml`) builds and pushes the ingest runner container image to Artifact Registry. It is typically triggered by a semantic version tag (`v*.*.*`) or manual workflow dispatch with an explicit `image_tag` input.

During **Publish**, the rendered workflow typically:

- Checks that `descriptor/data-product-descriptor.json` exists and is valid JSON (for example with `python -m json.tool`).
- Installs the runner package with `pip install -e ./application`.
- Runs `terraform fmt -check -recursive infrastructure`, then `terraform init -backend=false -input=false` and `terraform validate` under `infrastructure/` (validate-only; no remote state).
- Authenticates to Google Cloud using **Workload Identity Federation** and the manifest parameters `wif_provider` and `wif_service_account`.
- Configures Docker for Artifact Registry, builds the ingest image, and pushes it with the resolved `image_tag`.

Publishing does **not** run **Terraform apply** against your environments; it only produces an **immutable image reference** (registry URI + tag) that **Deploy** consumes later.

## Data product deployment

**Deploy** (rendered `.github/workflows/deploy.yml`) runs **Terraform apply** for **one** manifest **`environments`** value and **one** **`image_tag`** that was already produced by **Publish**.

During **Deploy**, the workflow typically:

- Checks out the repository.
- Resolves **`environment`** and **`image_tag`**: from **workflow_dispatch** (inputs **`environment`**—must match a descriptor **`lifecycleInfo`** key—and **`image_tag`**), or from **repository_dispatch** with event type **`deploy-ingest`** and **`client_payload`** fields **`environment`** and **`image_tag`**.
- Authenticates to Google Cloud using **Workload Identity Federation** with the manifest parameters **`wif_provider`** and **`wif_service_account`**.
- Runs **`terraform init`** in **`infrastructure/`** against the remote GCS backend using **`TF_STATE_BUCKET`** / **`TF_STATE_PREFIX`** (from instantiated manifest: `tf_state_bucket_address`, `tf_state_prefix`).
- Runs **`terraform apply -auto-approve`** in **`infrastructure/`**, passing (among others) **`gcp_project_id`**, **`gcp_region`**, **`environment`**, **`data_product_name`** (`dpName`), **`gcs_staging_bucket`**, **`bq_dataset_id`**, **`bq_partition_field`**, **`bq_cluster_fields_csv`**, **`cursor_field`**, **`row_discriminator_column`**, **`postgres_secret_id`**, **`bigquery_secret_id`**, **`artifact_registry_repository`**, **`cloud_run_job_name`**, **`image_name`**, and **`image_tag`**.

That apply **creates or updates**:

- The **BigQuery** dataset for loads.
- The **GCS** staging bucket used by **dlt**.
- The **Cloud Run Job** pinned to the published container **`image_tag`**, plus the job **service account** and **IAM** needed for BigQuery, GCS, and Secret Manager access.
- **Secret Manager** mounts (paths) for PostgreSQL and BigQuery credentials on the job.

**After a successful deploy**, operators **run the Cloud Run Job** (on demand, Cloud Scheduler, or another orchestrator) to execute an ingest.

## Environment variables

### Cloud Run Job (ingest container)

These are set on the job by Terraform (see `**infrastructure/cloud_run.tf`**) and are what the Python runner expects at runtime:


| Variable                                 | Role                                                                                                            |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `**DESCRIPTOR_PATH`**                    | Filesystem path to the DPDS JSON inside the image (default `**/app/descriptor/data-product-descriptor.json**`). |
| `**SOURCES__POSTGRES__CREDENTIALS**`     | Path to the mounted Postgres secret file (read by **dlt** / SQLAlchemy URL builder).                            |
| `**DESTINATION__BIGQUERY__CREDENTIALS`** | Path to the mounted BigQuery service account JSON.                                                              |
| `**INGEST_GCS_STAGING`**                 | `gs://` URL for **dlt** file staging.                                                                           |
| `**INGEST_GCP_PROJECT_ID`**              | GCP project id for BigQuery loads.                                                                              |
| `**INGEST_BQ_PARTITION_FIELD`**          | Partition column name on the target table.                                                                      |
| `**INGEST_BQ_CLUSTER_FIELDS**`           | Comma-separated clustering column names.                                                                        |
| `**INGEST_CURSOR_FIELD**`                | Optional incremental cursor column for Postgres extracts (empty string for full snapshots).                     |
| `**INGEST_ROW_DISCRIMINATOR_COLUMN**`    | Column name injected on each row with the **source schema** name (multi-schema consolidation).                  |


Optional / local-only variables read by the application code (not necessarily set by Terraform in production):


| Variable                      | Role                                                                                                                         |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `**CURSOR_STATE_PATH`**       | JSON file path for per-port cursor watermarks (defaults under `/tmp` if unset).                                              |
| `**TRANSFORM_HOOK_IDENTITY`** | Set to `**1**` only for smoke tests to bypass `**transform_hook**` mapping (rows must already match the output JSON Schema). |


### GitHub Actions (workflows)

**Publish** workflow `**env`** includes `**GCP_PROJECT_ID`**, `**GCP_REGION**`, `**ARTIFACT_REPO**`, `**IMAGE_NAME**` (fixed to `**ingest-runner**`), resolved `**IMAGE_TAG**`, and uses WIF for `**google-github-actions/auth**`.

**Deploy** workflow sets `**GCP_PROJECT_ID`**, `**GCP_REGION`**, `**TF_STATE_BUCKET**`, `**TF_STATE_PREFIX**`, `**ARTIFACT_REPO**`, `**IMAGE_NAME**`, and resolves `**DEPLOY_ENVIRONMENT**` / `**IMAGE_TAG**` from dispatch inputs.

## Normative references

- [DPDS](https://dpds.opendatamesh.org/specifications/dpds/)
- [Apache Velocity](https://velocity.apache.org/engine/devel/user-guide.html)
- Your platform’s **ODM blueprint manifest** specification for `**blueprint-manifest.yaml`**

## Where to go next

- **Python pipeline and modules:** `[application/README.md](../application/README.md)`
- **Manifest parameters and protected paths:** `[blueprint-manifest.yaml](../blueprint-manifest.yaml)` at repository root

