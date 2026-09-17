# Performance Rules

Configure deterministic checks and interpret PASS, FAIL, NOT_EVALUATED, and ERROR.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Current rule behavior](#current-rule-behavior)
- [Rule definition example](#rule-definition-example)
- [Report outcomes](#report-outcomes)
- [Replica rule limitation](#replica-rule-limitation)
- [Next steps](#next-steps)

## Current rule behavior

The rule analyzer consumes entity-summary rows during HTML generation. It supports `<=`, `>=`, `<`, `>`, `==`, and `!=`. A component selector of `*` applies across components; metric labels must match the readable names in the summary.

Current sample rules are:

| Rule | Statistic | Threshold |
| --- | --- | --- |
| CPU p95 | CPU Usage (%) / p95 | <= 80 |
| Memory p95 | Memory Usage (%) / p95 | <= 85 |
| CPU maximum | CPU Usage (%) / maximum | <= 95 |
| Replica count | replica_count | >= 1 |

These are initial sample thresholds, not confirmed business acceptance criteria. In particular, the replica rule checks maximum observed simultaneous pods; it does not establish continuous availability.

Missing matching summary rows or unavailable statistics can generate individual FAIL checks. Rule evaluation returns individual checks, passed/failed counts, failed components, and an overall result. Disabling the analyzer yields `NOT_EVALUATED`. An enabled analyzer with no failed checks computes `PASS`, so check the number of checks as well as the overall label.

**Execution success and performance acceptance are separate.** Exit code 0 means the pipeline finished. A generated HTML report can still contain a performance FAIL. The API uploader publishes after exit code 0 regardless of the report's performance verdict.

## Rule definition example

Merge rules into the existing configuration:

```yaml
rule_analyzer:
  enabled: true
  rules:
    - rule_id: "dts-cpu-p95"
      description: "DTS CPU p95 stays within the agreed limit"
      enabled: true
      component_name: "dts"
      metric_name: "CPU Usage (%)"
      statistic: "p95"
      operator: "<="
      threshold: 80
```

The threshold is an example. Confirm a business acceptance limit before treating it as a release criterion. Matching uses the summary's readable metric name, not the raw key `cpu_pct` in this example.

## Report outcomes

| Outcome | Interpretation |
| --- | --- |
| PASS | No generated checks failed. Verify enabled rules, check count, and metric coverage. |
| FAIL | At least one generated rule check failed. Inspect actual value, threshold, and component. |
| NOT_EVALUATED | Rule analysis was disabled. |
| ERROR | HTML reporting captured a rule configuration/evaluation error. |

Rule FAIL or ERROR does not inherently stop HTML generation or make the orchestrator exit nonzero. Neither outcome is currently returned as a persisted API run result.

## Replica rule limitation

The count is based on pod names in normalized timestamp records, including buckets with missing data. A threshold of at least one therefore does not establish that one replica was active for the whole window. Define separate data-completeness and availability requirements when those are acceptance criteria.

## Next steps

- [Results Details](07-RESULTS-PROCESSING-DETAILS.md) for statistic semantics.
- [Running PerfAgent](04-RUNNING-PERFAGENT.md) to regenerate reports.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
