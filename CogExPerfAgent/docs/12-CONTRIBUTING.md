# Contributing Guide

Extend the current implementation and keep documentation consistent with observable behavior.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Before changing code](#before-changing-code)
- [Add an entity or component](#add-an-entity-or-component)
- [Add a metric](#add-a-metric)
- [Add a collector type](#add-a-collector-type)
- [Validate behavior](#validate-behavior)
- [Change description](#change-description)
- [Keep these guides current](#keep-these-guides-current)
- [Next steps](#next-steps)

## Before changing code

Use [Setup](02-SETUP.md) to prepare an environment. Inspect local Git changes so existing work is preserved. Read the guide for the subsystem being changed and identify which output or API contract is affected.

These are project-specific documentation recommendations; use the team's established branch, review, and release process. This guide does not define an unverified repository governance policy.

## Add an entity or component

1. Define or reuse a component in `config/components.yaml`.
2. Select its implemented collector type, index, and source filters.
3. Reference the component key under an entity in `config/entities.yaml`.
4. Run a known small window and inspect returned groups and raw query.
5. Confirm normalized data, summaries, charts, and applicable rule checks.

Adding another component with the existing Kubernetes query shape can be a configuration-only change. See [Configuration](05-CONFIGURATION.md) for a minimal example.

## Add a metric

1. Define the field, supported aggregation, unit, and scale in `collector_types.yaml`.
2. Set visibility and component aggregation in reporting summaries and charts.
3. Confirm long/wide output values and summary interpretation.
4. Add any acceptance rule using the summary's readable metric name.
5. Update [Results Details](07-RESULTS-PROCESSING-DETAILS.md) and [Rules](10-PERFORMANCE-RULES.md).

## Add a collector type

Implement a collector using the existing base contract and register it in `app/registry.py`. Add query building and a normalizer suited to the response, then register normalization support in `app/result_aggregator/main.py`. Validate downstream summary and chart compatibility with its record structure.

Changing a YAML `query_builder` label alone does not dynamically load a new query builder. The Kubernetes collector instantiates its builder in code. Commented transaction/SQL/Kafka/APM examples are design starting points, not functioning collectors.

## Validate behavior

| Change | Useful verification |
| --- | --- |
| API or imports | Compile relevant modules; import the FastAPI application; exercise request validation and failure handling. |
| Blob uploader | Existing mocked tests plus meaningful coverage for any changed failure or path behavior. |
| Query/configuration | Entity resolution, exact filters, start/end boundaries, enabled metrics, grouping completeness. |
| Normalization/statistics | Scale handling, missing values, interpolation, per-timestamp component aggregation. |
| Report/rules | Readable names, thresholds, ERROR and no-data cases, actual asset links. |
| Packaging | Build/import checks with the declared dependencies and configured listener port. |
| Documentation | Relative link checks, command/field consistency, no invented endpoints or completed roadmap claims. |

## Change description

Describe the concrete behavior change, affected inputs/outputs, verification performed, and known limits. Distinguish a mocked test from a live integration run. Do not include credential values or imply that a historical deployment proves a new change.

## Keep these guides current

Update the relevant numbered guide and [Build Status](15-BUILD-STATUS.md) when a feature becomes implemented. Add new guides to [INDEX](INDEX.md), preserve unique numbering, and verify all relative links after renaming. Keep deployment evidence dated.

## Next steps

- [Architecture](APPROACHES-AND-ARCHITECTURE.md) for the source map and design choices.
- [Roadmap](16-ROADMAP.md) for proposed work and completion evidence.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
