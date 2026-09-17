# Build Status and Verification

Record what is implemented, the historical deployment milestone, and the limits of current verification.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Documentation evidence](#documentation-evidence)
- [Implemented capabilities](#implemented-capabilities)
- [Historical deployment milestone](#historical-deployment-milestone)
- [Verification and test coverage](#verification-and-test-coverage)
- [Documentation package validation](#documentation-package-validation)
- [Next steps](#next-steps)

## Documentation evidence

CogExPerfAgent collects Kubernetes container metrics from Elasticsearch for a selected business entity and test window, turns them into time series and statistical summaries, generates charts and an HTML performance report, and evaluates configurable acceptance rules. Its API can run this pipeline in a container and publish the execution artifacts to Azure Blob Storage.

This document describes the inspected working tree, including implementation files that were not yet committed when reviewed. The repository HEAD at inspection was `aeb5601d` (`added mcp details`). It is an implementation snapshot, not a claim that every local change has been committed, pushed, or deployed.

Evidence is separated as follows:

- **Code verified:** behavior found in the local source and configuration on 7 September 2026.
- **Historical deployment evidence:** the successful Strato run recorded on 4 September 2026. The live environment was not rechecked for this documentation update.
- **Remaining work:** absent functionality, incomplete integration, and follow-up decisions identified below.

The metrics source is Elasticsearch. The agent analyzes an existing test window; it does not generate application load or execute business transactions itself.

## Implemented capabilities

| Capability | Current implementation |
| --- | --- |
| Entity-based collection | Entities reference reusable component definitions; an optional component argument narrows the run. |
| Kubernetes collector | Collects CPU and memory metrics through configurable Elasticsearch aggregation queries. |
| Configuration separation | Application settings, collector definitions, components, entity membership, reporting, and acceptance rules live in separate YAML files. |
| Raw result retention | Saves a JSON result for each collected component. |
| Normalized outputs | Produces JSON, long CSV, and wide CSV time series. |
| Statistical summaries | Produces pod/container and component summaries with average, minimum, maximum, p90, p95, p99, and peak information. |
| Charts | Produces an entity overview and component charts with pod series. |
| HTML report | Combines the test timeframe, summaries, charts, and rule results into an execution-specific PSR report. |
| Rule analysis | Applies numeric thresholds and exposes performance PASS/FAIL within the report. |
| Command-line orchestration | Runs collection, normalization, summary generation, chart generation, and HTML generation in sequence. |
| HTTP API | Provides health, configuration-file presence checks, and asynchronous run acceptance. |
| Blob publication | API-triggered successful executions upload their full output folder to a configured Azure Blob container. |
| Container packaging | Python 3.12 image with a non-root user and Uvicorn API entry point. |
| MCP integration | Local stdio tools exist for connectivity, listing executions, reading summaries, and starting a run; packaging and output-path alignment remain incomplete. |
| Automated tests | Two mocked Blob uploader tests exist; the collector test file is currently empty. |

LLM analysis is not implemented: `app/llm_analyzer/llm_analyzer.py` is empty. Transaction, SQL, Kafka, and APM collector ideas appear as commented examples; only `kubernetes` is registered in `app/registry.py`.

## Historical deployment milestone

Historical session evidence from 4 September 2026 records:

- An image tagged `2026.09.04.6` was built and pushed for `cogex-perf-agent`.
- Execution `item-CIG_DTS-20260904T112414Z-408057a5` processed four components with zero collection failures.
- The run generated five chart reports and completed the pipeline with exit code 0.
- The execution folder was published to Azure Blob Storage, and publication was confirmed by the user.

This is historical evidence, not a fresh live-environment health check. The recorded follow-ups were to restore appropriate authentication, disable the temporary smoke-test Job, retain `restart_on_change=true`, and complete the Classic File Share configuration migration. Their current deployment status was not verified for this document.

## Verification and test coverage

This documentation update was based on source/configuration inspection and historical deployment records. It did not run a new Elasticsearch collection, deploy an image, or upload artifacts.

`tests/test_blob_uploader.py` contains two mocked tests: recursive Blob path preservation with client closure, and the missing connection-string error. These do not contact Azure. `tests/test_collector.py` is empty, so the current tests do not establish collection, query completeness, normalization, statistical, rules, API lifecycle, or end-to-end correctness.

Useful checks before the next image build, in a prepared development environment, are:

```shell
python -m py_compile app/api.py app/blob_uploader.py
python -c "from app.api import app; print(app.title)"
python -m pytest tests/test_blob_uploader.py -q
```

These are recommended verification commands, not results claimed for this documentation-only change. A previous deployment failed on an indentation error during API import, making the import check particularly useful. A deployment acceptance check should separately confirm process readiness, a known test-window run, subprocess completion, Blob upload completion, and readable report assets.

## Documentation package validation

These modular guides were created using the UXPerf repository's documentation organization as a reference: a root overview, a categorized index, numbered guides, standalone goals/architecture documents, and focused Stratosphere guides. Content reflects PerfAgent source rather than the other repository's test framework.

Documentation links and Markdown structure are checked separately from application functionality. Commands in the guides are examples or recommended checks unless explicitly identified as historical execution evidence.

## Next steps

- [Roadmap](16-ROADMAP.md) for remaining work.
- [Contributing](12-CONTRIBUTING.md) for maintaining the evidence as implementation changes.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
