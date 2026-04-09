# Blueprint: `source-aligned`

## What this blueprint is about

This blueprint defines a **source-aligned data product** : operational data is **landed immutably** in raw storage, **transformed and loaded** (here with [dlt](https://dlthub.com/)), and **exposed** to consumers via your catalog or warehouse. It is a **monorepo template**—Terraform, pipeline, and CI stubs are included so a team gets a consistent baseline; **domain-specific ingestion, schemas, and production wiring are left for you to implement** after instantiation.

This folder holds **blueprint metadata** only: the manifest (`[blueprint.yaml](blueprint.yaml)`) and this documentation. The **Data Product Descriptor Specification (DPDS) 1.0.0** template is at the repository root: `[../data-product-descriptor.json.vm](../data-product-descriptor.json.vm)`. The Velocity README that becomes the **data product** repo root (`../README.md.vm`) is product documentation, not part of the blueprint definition folder.

## Contents


| File                                                                       | Purpose                                                                                                                                                                       |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `[blueprint.yaml](blueprint.yaml)`                                         | Manifest: parameters, protected paths, `instantiation.strategy: monorepo`.                                                                                                    |
| `[../data-product-descriptor.json.vm](../data-product-descriptor.json.vm)` | DPDS [1.0.0](https://dpds.opendatamesh.org/specifications/dpds/1.0.0/) template (JSON + Apache Velocity), rendered at instantiation (e.g. to `data-product-descriptor.json`). |


## What this blueprint provisions

- **Infrastructure (Terraform):** `infrastructure/` with a protected `core` module — S3 raw/curated buckets, lifecycle, Glue database stub, IAM, shared VPC data sources.
- **Transformations (dlt):** `pipeline/` — skeleton (`source_aligned_pipeline.py`, `settings.py` from `settings.py.vm`), optional PII hashing via `enable_pii_masking`.
- **CI/CD:** `.github/workflows/cd-deploy.yml.vm` → `cd-deploy.yml` — matrix over manifest `environments` (job names `cd-deploy-<env>`). Use [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment) for each name if you rely on the job `environment:` key.

## After the blueprint has been instantiated

Instantiation renders `*.vm` templates and applies parameters; the platform may relocate the product README and record lineage under `.odm/blueprint/`. **From there, treat the repo as a real data product** and complete the following:

1. **Infrastructure** — Run Terraform against the target stage: set `environment` (and other vars) per deploy, e.g. `TF_VAR_environment` or `terraform.tfvars`, with credentials and backend appropriate for each account/region. Replace workflow **placeholder** deploy steps with real `terraform plan` / `apply` (and approvals) as your organization requires.
2. **Pipeline** — Replace the example `main_entity` resource with real sources (files in raw S3, databases, APIs, CDC). Switch the dlt **destination** from the local default (`duckdb` in the skeleton) to your production target (e.g. filesystem/S3, Athena, warehouse). Ensure `pipeline/settings.py` is present (rendered from `settings.py.vm`).
3. **Descriptor** — Update the rendered **data product descriptor** with concrete **output port** contracts (e.g. DatastoreAPI or OpenAPI) once curated tables and interfaces are stable; 
4. **CI/CD** — Configure secrets (e.g. AWS, Terraform state), wire **dlt** execution or scheduling into the pipeline, and align **GitHub Environment** protection rules with your `environments` matrix.

## Parameters (summary)


| Key                                                             | Role                                                                             |
| --------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `environments`                                                  | Deployment stage names (e.g. `dev`, `prod`) for DPDS `lifecycleInfo` and tags    |
| `domain_slug`                                                   | DNS-like segment for buckets and Glue identifiers                                |
| `dpDomain`, `dpName`, `dpFqn`, `dpDisplayName`, `dpDescription` | Reserved — auto-filled from Data Product information (`dpDescription` optional)  |
| `dpOwnerId`, `dpOwnerName`                                      | Reserved — auto-filled from profile (`dpOwnerId` used for Terraform FinOps tags) |
| `data_retention_days`                                           | Raw-layer S3 expiration window                                                   |
| `enable_pii_masking`                                            | Example hashing of sensitive fields in the dlt resource                          |


## Platform registration

Point the linked Git repository to:

- **Manifest:** `blueprint/blueprint.yaml`
- **Descriptor template:** `data-product-descriptor.json.vm` (repository root)
- **README template (data product):** `README.md` (from `README.md.vm` after Velocity)

