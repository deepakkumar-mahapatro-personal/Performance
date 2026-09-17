# Running PerfAgent

Run a full entity, narrow collection to a component, or regenerate existing artifacts.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Execution inputs](#execution-inputs)
- [Full entity run](#full-entity-run)
- [Single component run](#single-component-run)
- [Collection only](#collection-only)
- [Regenerate downstream stages](#regenerate-downstream-stages)
- [Execution stages and failure behavior](#execution-stages-and-failure-behavior)
- [API execution](#api-execution)
- [Next steps](#next-steps)

## Execution inputs

| Input | CLI argument | Required | Behavior |
| --- | --- | --- | --- |
| Entity | `--entity` | Yes | Resolves a component list from `entities.yaml`. |
| Start | `--start-time` | Yes | ISO-8601 lower bound; inclusive in the query. |
| End | `--end-time` | Yes | ISO-8601 upper bound; exclusive in the query. |
| Interval | `--interval` | No | Uses collector default `30s` when omitted. |
| Component | `--component` | No | Must be a member of the selected entity. |
| Execution ID | `--execution-id` | No | CLI generates `<entity>-<UTC timestamp>` when omitted. |

Use timezone-qualified timestamps and a fresh execution ID for each distinct test. Automatic CLI IDs have second precision; unlike API IDs, they do not have a UUID suffix. Closely timed same-entity CLI runs can collide.

## Full entity run

From the project root with credentials and output configured:

```bash
python -m app.main --entity item-CIG_DTS --start-time 2026-09-04T10:00:00Z --end-time 2026-09-04T10:30:00Z --interval 30s
```

The timestamps are examples. Both configured entities, `item-CIG_DTS` and `orderRelease-CIG_DTS`, currently reference the same four components. Their names describe business-flow grouping; the metrics themselves are Kubernetes resource utilization.

## Single component run

```bash
python -m app.main --entity item-CIG_DTS --component dts --start-time 2026-09-04T10:00:00Z --end-time 2026-09-04T10:30:00Z --interval 30s --execution-id item-dts-investigation-001
```

This is useful when confirming one component's source filters. Downstream stages operate on the files under this execution/entity. Use a new ID so old component artifacts cannot be mixed into the new run.

## Collection only

```bash
python -m app.result_collector.main --entity item-CIG_DTS --component dts --start-time 2026-09-04T10:00:00Z --end-time 2026-09-04T10:30:00Z --execution-id item-dts-raw-001
```

Inspect the raw result's `metadata`, `query`, and `elasticsearch_response` to understand what was requested and returned. This command does not generate summaries or publish to Blob.

## Regenerate downstream stages

Use an existing execution ID with its raw artifacts present:

```bash
python -m app.result_aggregator.main --execution-id item-dts-raw-001 --entity item-CIG_DTS
python -m app.result_aggregator.summary_main --execution-id item-dts-raw-001 --entity item-CIG_DTS
python -m app.visualization.chart_main --execution-id item-dts-raw-001 --entity item-CIG_DTS
python -m app.reporting.html_report_main --execution-id item-dts-raw-001 --entity item-CIG_DTS
```

These commands can replace derived files. Rerunning only summaries/charts/HTML does not query Elasticsearch again. Changes to normalization scale require regenerating normalized outputs first. Keep the configuration used for each interpretation; the current pipeline does not automatically save a full effective configuration snapshot.

## Execution stages and failure behavior

1. Collect enabled components and write raw JSON.
2. Normalize aggregation responses to JSON and CSV.
3. Build pod and component statistical summaries.
4. Build entity and component charts.
5. Build the HTML report and evaluate rules.

Components are collected sequentially. Handled per-component failures allow remaining collection attempts, but any final failed-component list makes collection fail. A failed processing subprocess stops the orchestration. Generated partial artifacts can remain for investigation.

The report's PASS/FAIL/ERROR result is separate from process exit status. An API run uploads only after the pipeline process exits 0, and it can upload a report with a performance FAIL.

## API execution

The API accepts a JSON request and returns an execution ID before work finishes. Use [API Reference](11-API-REFERENCE.md) for a complete request example. It currently has no polling, cancellation, or artifact-download endpoint and no durable execution queue.

## Next steps

- [Results Processing](06-RESULTS-PROCESSING.md) to locate outputs.
- [Results Processing Details](07-RESULTS-PROCESSING-DETAILS.md) to interpret metrics.
- [Rules](10-PERFORMANCE-RULES.md) to understand acceptance checks.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
