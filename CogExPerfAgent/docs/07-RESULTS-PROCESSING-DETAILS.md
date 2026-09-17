# Results Processing Details

Explain metric mapping, normalization fields, statistics, missing data, and coverage limitations.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Collection semantics](#collection-semantics)
- [Statistical processing](#statistical-processing)
- [Raw JSON contract](#raw-json-contract)
- [Normalized data fields](#normalized-data-fields)
- [Summary columns](#summary-columns)
- [Worked interpretation example](#worked-interpretation-example)
- [Coverage limits](#coverage-limits)
- [Report timeframe and chart continuity](#report-timeframe-and-chart-continuity)
- [Next steps](#next-steps)

## Collection semantics

The query builder requests aggregation results (`size: 0`) rather than raw document hits. It applies required project, stage, geography, and dataset filters, plus resource/container filters when supplied. Current shared defaults select stage `staging`, geography `us`, and dataset `kubernetes.container`.

The test range includes the start and excludes the end: `gte start_time`, `lt end_time`. Results are grouped by container name and pod name, then bucketed using a fixed UTC interval. The configured group limit is 100. The builder uses `multi_terms` without pagination, so workloads with more groups require a completeness review.

Containers named `istio-proxy`, `auth-proxy`, `istio-init`, and `auth` are excluded by the current configuration.

| Metric | Elasticsearch field | Bucket aggregation | Normalization scale | Default summary/chart visibility |
| --- | --- | --- | --- | --- |
| `cpu_pct` | `kubernetes.container.cpu.usage.limit.pct` | Average | Multiply by 100 | Enabled as CPU Usage (%). |
| `cpu_nanocores` | `kubernetes.container.cpu.usage.nanocores` | Average | 1 | Disabled; retained in normalized data. |
| `mem_pct` | `kubernetes.container.memory.workingset.limit.pct` | Average | Multiply by 100 | Enabled as Memory Usage (%). |
| `mem_bytes` | `kubernetes.container.memory.workingset.bytes` | Average | 1 | Disabled; retained in normalized data. |

Percentages are based on the Elasticsearch limit-relative fields. They should be interpreted according to those source fields, not as host-wide utilization.

## Statistical processing

Normalization flattens the grouped aggregation response into timestamped metric records with execution/entity/component identity, group fields, scaled values, and data-availability information. It preserves collected metrics even when they are hidden in charts and summaries.

Pod summaries describe individual container/pod groups. Component summaries first combine valid values at each timestamp and then calculate statistics over those combined points. The configured component combination is average for CPU/memory percentages and sum for absolute CPU/memory metrics when those are enabled for reporting.

The statistics include average, minimum, maximum, p90, p95, p99, peak value, and peak timestamp. Percentiles use interpolation over sorted values. These are percentiles of bucketed utilization values, not transaction response-time percentiles. The selected interval therefore affects the resulting statistics and may smooth short spikes.

`replica_count` is the maximum count of distinct pod names represented at a timestamp in normalized records. The counting code does not filter by `has_data` or `document_count`, so empty histogram buckets can contribute pod names. It is not the minimum number available throughout the test and does not represent desired replica count from a Kubernetes deployment specification.

The entity summary contains component-level metric rows for the selected business entity; it is not a single end-to-end transaction latency or throughput measurement.

## Raw JSON contract

The collector writes three top-level objects: `metadata`, `query`, and `elasticsearch_response`. Metadata records component identity, collector type, index, time range, interval, component filters, and returned pod/container group count. The saved query shows the effective Elasticsearch request, including default filters.

## Normalized data fields

| Field or group | Meaning |
| --- | --- |
| `execution_id`, `entity_name`, `component_name` | Artifact identity and source grouping. |
| `component_display_name`, `collector_type` | Presentation identity and collector name. |
| `timestamp`, `timestamp_epoch_ms` | Bucket timestamp representations from the response. |
| `document_count` | Source document count in the group/time bucket. |
| `kubernetes.container.name`, `kubernetes.pod.name` | Current group fields retained with their exact source names. |
| `metric_name`, `metric_display_name` | Metric key and collector-level display name/fallback. |
| `raw_value`, `value` | Raw aggregate and scaled numeric value. |
| `unit`, `scale_factor` | Metric unit and conversion factor. |
| `has_data` | Whether normalization produced a non-null scaled value. |

`timeseries.json` contains `metadata`, `columns`, and `records`. The long CSV uses the normalized column list. The wide CSV pivots metric values into separate columns for inspection. Missing values remain missing rather than automatically becoming zero.

## Summary columns

The configured entity summary columns are execution/entity/component identity, `replica_count`, readable `metric_name`, `average`, `minimum`, `maximum`, `p90`, `p95`, `p99`, `peak_value`, and `peak_timestamp`. Pod summaries add container and pod identity and omit replica count.

Summary statistics use records with `has_data: true` and numeric values. CPU/memory percentage component points are arithmetic averages across valid group values at a timestamp. Different container limits are not used as weights.

## Worked interpretation example

Suppose two pod groups have CPU percentages of 20 and 60 at a timestamp. The default component percentage is `(20 + 60) / 2 = 40`. It is not a sum of 80 and is not necessarily the percentage of total combined CPU limits. Component percentiles are then calculated across these component values over time.

If a pod has no valid value at a timestamp, it does not contribute to the summary's numeric average. Its normalized bucket can still contribute to `replica_count`. Review data coverage before treating that count as availability evidence.

## Coverage limits

The query includes `min_doc_count: 0` but does not set extended histogram bounds. Do not assume every group has buckets across the full requested test range. The `multi_terms` group size is 100 without pagination. A zero-group response can complete a collection request without proving useful metric coverage.

## Report timeframe and chart continuity

The HTML header derives its displayed timeframe from the earliest and latest timestamps in normalized records, including empty buckets. It does not display the original requested start/end directly. In particular, the latest bucket timestamp is not the exclusive end boundary of the request. Use saved metadata and the raw query when confirming the exact requested window.

Charts filter unavailable metric points and connect the remaining timestamps. A continuous line therefore does not prove continuous sampling. With the configured pod series field, values from multiple container records belonging to the same pod and timestamp are averaged for that plotted series.

## Next steps

- [Configuration](05-CONFIGURATION.md) to change selected metrics.
- [Rules](10-PERFORMANCE-RULES.md) to map summaries to checks.
- [Troubleshooting](08-TROUBLESHOOTING.md) for sparse or surprising results.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
