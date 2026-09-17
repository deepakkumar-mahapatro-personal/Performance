# Configuration Guide

Configure applications, collector types, reusable components, entity membership, reporting, and rules.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Configuration files](#configuration-files)
- [Current entities and components](#current-entities-and-components)
- [Configuration limitations to account for](#configuration-limitations-to-account-for)
- [Add a component to an entity](#add-a-component-to-an-entity)
- [Configuration precedence](#configuration-precedence)
- [Verification after a configuration change](#verification-after-a-configuration-change)
- [Validation scope and logging](#validation-scope-and-logging)
- [Next steps](#next-steps)

## Configuration files

| File | Responsibility | Main settings |
| --- | --- | --- |
| `config/application.yaml` | Environment and runtime settings | Elasticsearch URL/authentication/TLS/timeout, output directory, collection and logging settings. |
| `config/collector_types.yaml` | How metrics are queried | Index defaults, timestamp field, interval, filter mappings, grouping, exclusions, metric fields, scaling. |
| `config/components.yaml` | Reusable component definitions | Enabled flag, collector type, index override, project/resource/container filter values. |
| `config/entities.yaml` | Business-flow membership | Entity names mapped to lists of component names. |
| `config/reporting.yaml` | Presentation and summary selection | Chart settings, enabled report metrics, summary columns and filenames, HTML options. |
| `config/rules.yaml` | Acceptance checks | Enabled rules, component and metric selectors, statistic, comparison operator, threshold. |

`ConfigLoader` validates that YAML files contain mappings and that required top-level configuration objects exist. The component/entity separation is implemented: `load_components()`, `load_all()`, and collection-time component resolution are present.

## Current entities and components

Both `item-CIG_DTS` and `orderRelease-CIG_DTS` reference these four enabled components:

| Component key | Display name | Additional selection |
| --- | --- | --- |
| `beacon-ingress` | Beacon Ingress | Resource `beacon-ingress-service`, container `service`. |
| `dts` | DTS | Resource `dts`; container unrestricted. |
| `dp` | Data Processor | Container `jdp-data-processor`; resource unrestricted. |
| `cis` | CIS | Resource `cw-asynchttp-psr-eus2-01`; container unrestricted. |

Each component also has its own project filter. Consult `components.yaml` for the environment-specific project values. All currently use `metrics-kubernetes.container-default`.

## Configuration limitations to account for

- `ConfigLoader()` defaults to the relative `config` directory. Setting `PERF_CONFIG_DIR` currently changes the readiness probe's directory without changing the pipeline's configuration directory.
- The query builder uses the explicit interval or the collector's `default_interval`, currently `30s`. Do not assume the application-level default interval controls the query.
- `reporting.tables` declares output switches, but the normalization entry point currently writes JSON, long CSV, and wide CSV unconditionally.
- The HTML builder generates `<execution-id>_PSR_Report.html` despite the configured HTML filename. It also expects the standard summary and chart filenames. Renaming these outputs requires coordinated changes.
- Some source comments still say component values belong in `entities.yaml`; the actual reusable definitions are in `components.yaml`.

## Add a component to an entity

The following is an illustrative component entry. Replace project/resource filters with values confirmed in Elasticsearch, and merge it into the existing `components` mapping:

```yaml
components:
  example-service:
    display_name: "Example Service"
    enabled: true
    collector_type: "kubernetes"
    index: "metrics-kubernetes.container-default"
    filters:
      project_name: "<project-name>"
      resource_name: "<resource-name>"
      container_name: null
```

Reference the same component key in `entities.yaml`:

```yaml
entities:
  example-flow:
    - example-service
```

These are fragments, not replacements for all current entries. `null` optional filters are omitted from the query; the required shared/default filters must still resolve. Selecting an entity with an undefined component produces a configuration error.

## Configuration precedence

| Setting | Resolution |
| --- | --- |
| Index | Component index, otherwise collector default index. |
| Query filters | Collector default filter values merged with component filters; component values win. |
| Query interval | Runtime interval, otherwise collector default interval, otherwise builder fallback. |
| Collected metrics | Enabled definitions in `collector_types.yaml`. |
| Summary/chart metrics | Enabled selections in the corresponding `reporting.yaml` sections. |
| Credentials | Process environment, with local dotenv loading in collection. |
| Configuration directory | Default `ConfigLoader()` uses project-relative `config`. |

## Verification after a configuration change

Run a small known window for the changed component. Compare saved query filters with the intended source labels, inspect returned groups, and verify raw-to-scaled metric values. Check report labels before adding rules that depend on them.

## Validation scope and logging

`ConfigLoader.load_all()` loads application, collector types, components, and entities. Reporting and rules are loaded separately by their stages. Validation is distributed; loading the application mapping does not validate every nested runtime field or external connection.

The `logging.level` and `logging.directory` settings are present in YAML but are not used by the inspected implementation. Operational diagnostics currently go to console output; no configurable file-log artifact is promised by these settings.

## Next steps

- [Environment Variables](03-ENVIRONMENT-VARIABLES.md) for credential scope.
- [Results Details](07-RESULTS-PROCESSING-DETAILS.md) for field and scale semantics.
- [Rules](10-PERFORMANCE-RULES.md) for acceptance thresholds.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
