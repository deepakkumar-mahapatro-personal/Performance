# CogExPerfAgent

Configuration-driven Kubernetes performance analysis using Elasticsearch, with HTML reporting and Azure Blob publication.

[Documentation Index](docs/INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## What PerfAgent does

Choose a business entity and an existing test window. PerfAgent collects Kubernetes CPU/memory metrics, generates normalized JSON and CSV, builds pod/component summaries and charts, and evaluates configurable rules in an HTML PSR report. The HTTP API can trigger the pipeline and publish artifacts to Azure Blob Storage.

**Source snapshot:** 7 September 2026, inspected working tree based on HEAD `aeb5601d`, including local uncommitted API/deployment work. The successful Strato run described in these guides is historical evidence from 4 September, not a fresh live-environment check.

## Quick start

From the `CogExPerfAgent` project directory, prepare a Python 3.12 environment, install `requirements.txt`, configure Elasticsearch credentials, and select a writable output root. Then run a known window:

```bash
python -m app.main --entity item-CIG_DTS --start-time 2026-09-04T10:00:00Z --end-time 2026-09-04T10:30:00Z --interval 30s
```

The timestamps are examples. Open the printed HTML report path and keep its execution folder intact. The [Quick Start](docs/01-QUICKSTART.md) and [Setup Guide](docs/02-SETUP.md) provide complete prerequisites and Windows/WSL instructions.

## Documentation

| Guide | Purpose |
| --- | --- |
| [Documentation Index](docs/INDEX.md) | All guides organized by task and audience. |
| [Goals and Objectives](docs/GOALS-AND-OBJECTIVES.md) | Purpose, scope, and implemented outcomes. |
| [Architecture](docs/APPROACHES-AND-ARCHITECTURE.md) | Pipeline, source modules, and design choices. |
| [Quick Start](docs/01-QUICKSTART.md) | First collection and report. |
| [Setup](docs/02-SETUP.md) | Local Python environments and prerequisites. |
| [Environment Variables](docs/03-ENVIRONMENT-VARIABLES.md) | Credentials, dotenv scope, and runtime variables. |
| [Running PerfAgent](docs/04-RUNNING-PERFAGENT.md) | Entity/component runs and stage reruns. |
| [Configuration](docs/05-CONFIGURATION.md) | Six YAML files and extension examples. |
| [Results Processing](docs/06-RESULTS-PROCESSING.md) | Generated files and pipeline stages. |
| [Results Details](docs/07-RESULTS-PROCESSING-DETAILS.md) | Fields, aggregation, percentiles, and missing data. |
| [Troubleshooting](docs/08-TROUBLESHOOTING.md) | Symptoms, causes, and corrective checks. |
| [Best Practices](docs/09-BEST-PRACTICES.md) | Comparable, interpretable, and reviewable runs. |
| [Performance Rules](docs/10-PERFORMANCE-RULES.md) | Thresholds and report outcome semantics. |
| [API Reference](docs/11-API-REFERENCE.md) | Endpoints, requests, and execution behavior. |
| [Contributing](docs/12-CONTRIBUTING.md) | Extend collectors, metrics, and documentation. |
| [MCP Integration](docs/13-MCP-INTEGRATION.md) | Existing tools and integration gaps. |
| [Blob Publication](docs/14-AZURE-BLOB-PUBLICATION.md) | Publication, artifact access, and limits. |
| [Build Status](docs/15-BUILD-STATUS.md) | Implemented capabilities and dated verification. |
| [Roadmap](docs/16-ROADMAP.md) | Proposed improvements and completion criteria. |
| [Container Build](docs/stratosphere/01-BUILD-DOCKER-IMAGE-LOCAL.md) | Build and inspect the API image. |
| [Stratosphere Deployment](docs/stratosphere/02-STRATOSPHERE-DEPLOYMENT.md) | Runtime, configuration mount, and storage contract. |

## Implemented capabilities

- Entity-to-component configuration with four current reusable components.
- Elasticsearch-only Kubernetes CPU and memory collection.
- Raw JSON, normalized long/wide tables, statistical summaries, PNG charts, and HTML reports.
- Configurable numeric performance rules.
- CLI orchestration, API run submission, and API-triggered Azure Blob upload.
- Local MCP tool source for running and reading results, with documented integration gaps.

## Project structure

```text
CogExPerfAgent/
  app/
    main.py                 Pipeline orchestration
    api.py                  HTTP execution wrapper
    blob_uploader.py        Artifact publication
    config_loader.py        YAML configuration loading
    elastic_client.py       Elasticsearch HTTP transport
    query_builders/         Aggregation query construction
    result_collector/       Component collection
    result_aggregator/      Normalization and summaries
    visualization/          PNG rendering
    reporting/              HTML report construction
    rule_analyzer/          Deterministic acceptance checks
    mcp_server.py           Local stdio integration
  config/                   Six YAML configuration files
  deploy/docker/Dockerfile  API image definition
  tests/                    Current uploader tests
  docs/                     Modular documentation
  requirements.txt          Python dependencies
```

## Status to understand before operation

The API returns 202 when a run is accepted. There is no durable queue or persisted run-status endpoint. Exit code 0 is generation success; the performance report may still show FAIL or ERROR. Azure publication is a separate outcome.

Classic File Share is the intended configuration source, while Azure Blob stores results. The pipeline still defaults to relative `config`; `PERF_CONFIG_DIR` currently affects only readiness. The container writes results to `/tmp/perf-agent/output` and listens on port 8080 despite an EXPOSE declaration of 8000.

Only the Kubernetes collector is implemented. LLM analysis and additional collector types remain future work. See [Build Status](docs/15-BUILD-STATUS.md) for evidence and [Roadmap](docs/16-ROADMAP.md) for follow-ups.

---

[Documentation Index](docs/INDEX.md)
