# Goals and Objectives

Explain what PerfAgent is intended to solve and what the current build can demonstrate.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Problem being addressed](#problem-being-addressed)
- [Objectives and current evidence](#objectives-and-current-evidence)
- [Users and reading paths](#users-and-reading-paths)
- [Current scope](#current-scope)
- [What a successful run should demonstrate](#what-a-successful-run-should-demonstrate)
- [Next steps](#next-steps)

## Problem being addressed

Performance investigations often require manually collecting resource metrics, correlating them with a test window, and assembling evidence for several services. CogExPerfAgent standardizes that workflow for Kubernetes metrics already stored in Elasticsearch.

## Objectives and current evidence

| Objective | Current implementation | Evidence to inspect |
| --- | --- | --- |
| Repeatable collection | Configured entities, reusable components, explicit time windows and intervals. | Config files and saved raw query. |
| Consistent metric interpretation | Shared normalization and statistical processing. | Time series, source metric mapping, summary code. |
| Reviewable performance results | CSV summaries, PNG charts, HTML report, numeric acceptance checks. | Complete execution artifact folder. |
| Automated execution entry point | CLI and an HTTP run-submission endpoint. | `app/main.py`, `app/api.py`. |
| Central result storage | Successful API executions publish to Azure Blob. | Uploader source and dated deployment milestone. |
| Configuration independent of image release | Classic File Share design established. | Migration and common path resolution remain incomplete. |
| Assisted access to local results | MCP tools implemented in source. | Packaging and path consistency still require work. |

## Users and reading paths

- Performance engineers configure a known test window, generate results, and evaluate utilization.
- Operators manage the API/container, runtime credentials, and result publication.
- Developers extend metric collection, result processing, and reporting.
- Reviewers use the build-status and roadmap guides to distinguish implemented behavior from proposed improvements.

## Current scope

The implemented collector analyzes Kubernetes CPU and memory using Elasticsearch. It does not execute load tests, derive transaction latency/TPS from these utilization fields, or use InfluxDB/Grafana as a data source. Additional Elasticsearch collector types and LLM analysis are future work.

## What a successful run should demonstrate

Use a selected entity and known time window, verify component/data coverage, generate linked report artifacts, and inspect meaningful acceptance checks. For API use, separately establish publication to the expected Blob prefix. Run completion, performance acceptance, and artifact publication are different outcomes.

The September 2026 historical deployment demonstrated collection and publication. It does not establish a durable queue, continuous availability validation, current production authentication, or completion of the File Share migration.

## Next steps

- [Architecture](APPROACHES-AND-ARCHITECTURE.md) explains the implementation.
- [Build Status](15-BUILD-STATUS.md) records evidence and boundaries.
- [Roadmap](16-ROADMAP.md) lists proposed follow-ups.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
