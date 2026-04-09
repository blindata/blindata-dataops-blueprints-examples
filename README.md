# Blindata DataOps blueprint examples

This repository holds **example blueprint source repositories** compatible with the Open Data Mesh **odm-blueprint-manifest** specification consumed by the blueprint platform (see `odm-platform-pp-blueprint-server`).

## Layout

| Path | Description |
|------|-------------|
| [`source-aligned/`](source-aligned/) | Monorepo, no composition: generic source-aligned data product skeleton (Terraform, **dlt** pipeline, CI workflow). |

## Registering a blueprint in the platform

Point the blueprint repository metadata to:

- **Manifest path** (`manifestRootPath`): `source-aligned/blueprint/blueprint.yaml` when this monorepo is the remote, or `blueprint/blueprint.yaml` if the data product blueprint is published as its own Git repository root.
- **Descriptor template** (`descriptorTemplatePath`): `source-aligned/data-product-descriptor.json.vm` (or `data-product-descriptor.json.vm` at the repository root for a standalone blueprint repo). Produces a [DPDS 1.0.0](https://dpds.opendatamesh.org/specifications/dpds/1.0.0/) JSON document at instantiation.
- **README path** (`readmePath`): `README.md` (generated from `README.md.vm` at instantiation).

Blueprint metadata and human documentation of the blueprint itself live under **`blueprint/`** (manifest and `blueprint/README.md`). The **DPDS descriptor template** is at the **repository root** (`data-product-descriptor.json.vm`), alongside the data-product README template (`README.md.vm`).

## Templating

Instantiation renders **Apache Velocity** templates: any file named `*.vm` is evaluated and written to the same path without the `.vm` suffix. Parameters from the manifest are available as **top-level** Velocity variables (for example `$domain_slug`, `$environments`), matching `InstantiateBlueprintVersionTemplatingOutboundPortImpl` in the blueprint server. Values such as the Terraform `environment` target are typically **not** manifest parameters — supply them in CI/CD when provisioning each stage.

After instantiation, the platform removes the source manifest path, writes lineage under `.odm/blueprint/blueprint-manifest.yaml`, and moves the README into `.odm/blueprint/` per repository configuration.
