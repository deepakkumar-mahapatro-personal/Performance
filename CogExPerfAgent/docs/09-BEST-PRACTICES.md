# Best Practices

Use consistent inputs, preserve interpretable results, and keep operational limits visible.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Choose comparable test windows](#choose-comparable-test-windows)
- [Separate completion from acceptance](#separate-completion-from-acceptance)
- [Preserve artifact context](#preserve-artifact-context)
- [Interpret utilization correctly](#interpret-utilization-correctly)
- [Manage configuration consistently](#manage-configuration-consistently)
- [Bound operational work](#bound-operational-work)
- [Keep secrets out of artifacts](#keep-secrets-out-of-artifacts)
- [Verify changes at the right level](#verify-changes-at-the-right-level)
- [Next steps](#next-steps)

## Choose comparable test windows

Record test start/end with timezones, the entity, selected components, and the aggregation interval. Compare runs using consistent intervals and component filters. Bucket averaging can smooth spikes; a coarser interval changes the statistical population.

## Separate completion from acceptance

Check pipeline completion, data coverage, rule outcome, and Blob publication independently. A 202 API response means accepted work; exit code 0 means generation completed; the HTML verdict describes evaluated performance checks; upload logs and artifacts describe publication.

An enabled rule analyzer with zero failed checks can display PASS even with zero enabled rules. Always examine check counts and data coverage. A report marked ERROR requires investigation of rule configuration or evaluation.

## Preserve artifact context

Keep the full execution folder so HTML-relative image and CSV references work. Use distinct execution IDs and avoid reusing an ID across tests. Record source revision and the effective nonsecret configuration alongside formal results until automatic run manifests are implemented.

## Interpret utilization correctly

CPU and memory percentages use limit-relative source fields and scaling by 100. Component percentage summaries average valid group values at each timestamp; they are not weighted by container resource limits. `replica_count` counts distinct pod names in normalized timestamp buckets, including records without metric data; it should not be used as a continuous availability measure.

## Manage configuration consistently

Use `components.yaml` for reusable definitions and `entities.yaml` for membership. Keep collected metric definitions in `collector_types.yaml`; choose displayed metrics in `reporting.yaml`. Rule selectors match the readable summary metric names.

Preserve standard summary/chart filenames until the HTML builder's fixed references are made configurable. Do not rely on `PERF_CONFIG_DIR` to change the pipeline directory in the current implementation.

## Bound operational work

The API has no application-level durable queue, bounded job concurrency, or persisted recovery. Start with controlled submissions appropriate to available resources. Consider long ranges, short intervals, the configured 100-group cap, and Matplotlib memory usage when sizing a run.

## Keep secrets out of artifacts

Use process environment or approved secret injection for credentials. Do not commit `.env` or save Azure connection strings in command examples or shared logs. Diagnostics should show presence or failure category without printing credential values.

## Verify changes at the right level

Run the existing mocked tests for uploader changes, import checks before image builds, and representative pipeline validation for changes to collection, normalization, or reporting. The present test suite is limited; passing it does not establish end-to-end correctness.

## Next steps

- [Contributing](12-CONTRIBUTING.md) for implementation extension steps.
- [Build Status](15-BUILD-STATUS.md) for current evidence and coverage.
- [Roadmap](16-ROADMAP.md) for the proposed operational improvements.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
