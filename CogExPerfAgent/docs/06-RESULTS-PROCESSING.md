# Results Processing

Follow each generation stage and locate the raw data, tables, charts, and final report.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Processing stages](#processing-stages)
- [Artifact directory](#artifact-directory)
- [Reading a report](#reading-a-report)
- [Reprocessing](#reprocessing)
- [Next steps](#next-steps)

## Processing stages

| Stage | Input | Output | Entry point |
| --- | --- | --- | --- |
| Collection | Entity, component filters, test window, Elasticsearch metrics. | Raw result per component. | `app.result_collector.main` |
| Normalization | Raw response and collector metric definitions. | Long records, normalized JSON, long/wide CSV. | `app.result_aggregator.main` |
| Summary generation | Normalized records and reporting metric selection. | Entity/component metric rows and pod summaries. | `app.result_aggregator.summary_main` |
| Chart generation | Normalized records and chart settings. | Entity and component PNGs. | `app.visualization.chart_main` |
| HTML generation | Summaries, chart paths, rules. | Execution-specific HTML PSR report. | `app.reporting.html_report_main` |
| Publication | Successful API execution folder. | Blob objects under execution ID. | `app.blob_uploader` called by API |

Collection and reporting can be run by the CLI. Publication is connected to the API path. The main orchestrator invokes all five generation stages; optional reporting configuration can disable portions, which must remain compatible with downstream file expectations.

## Artifact directory

The currently configured container output root is `/tmp/perf-agent/output`. With current filenames and enabled outputs, the structure is:

```text
<output-root>/<execution-id>/
  raw/<entity>/<component>/kubernetes.json
  aggregated/<entity>/entity-summary.csv
  aggregated/<entity>/<component>/timeseries.json
  aggregated/<entity>/<component>/timeseries.csv
  aggregated/<entity>/<component>/timeseries-wide.csv
  aggregated/<entity>/<component>/pod-summary.csv
  visualizations/<entity>/entity-performance-report.png
  visualizations/<entity>/<component>/component-performance-report.png
  reports/<entity>/<execution-id>_PSR_Report.html
```

Raw JSON supports investigation; normalized tables support further analysis; summaries provide compact statistics; PNGs show trends; the HTML report is the main human-readable result.

The HTML report uses relative artifact paths. Download and preserve the execution folder structure when viewing locally. A standalone downloaded HTML file may lose chart and CSV references. The API does not currently provide an artifact-download endpoint.

## Reading a report

Start with the execution ID and displayed bucket timeframe. Confirm the requested start/end in normalized metadata; the HTML header uses the earliest/latest record timestamps. Review the performance verdict and the number of rule checks. Use entity-summary rows to compare component-level utilization, then inspect pod summaries and component charts to understand individual group behavior. Follow raw and normalized data when a value or filter needs explanation.

For the current four-component entity with all generation outputs enabled, the structure implies 27 files: four raw JSON files, twelve normalized files, five summary CSVs, five PNG charts, and one HTML report. The actual file count must be checked from the execution; disabling outputs or adding components changes it.

## Reprocessing

Use the separate stage commands in [Running PerfAgent](04-RUNNING-PERFAGENT.md). Changes to selected report metrics can be applied from existing normalized data. Changes to scale or raw query semantics may require normalization or collection again. Avoid combining old and new component files under one execution ID.

## Next steps

- [Results Details](07-RESULTS-PROCESSING-DETAILS.md) for the data model and interpretation.
- [Rules](10-PERFORMANCE-RULES.md) for PASS/FAIL semantics.
- [Blob Publication](14-AZURE-BLOB-PUBLICATION.md) for published results.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
