# Quick Start Guide

Prepare a local environment and generate your first PerfAgent report from an existing test window.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Before you start](#before-you-start)
- [1. Prepare Python](#1-prepare-python)
- [2. Configure credentials and output](#2-configure-credentials-and-output)
- [3. Run a known test window](#3-run-a-known-test-window)
- [4. Check the generated report](#4-check-the-generated-report)
- [5. Use the API when you need Blob publication](#5-use-the-api-when-you-need-blob-publication)
- [Expected completion checks](#expected-completion-checks)
- [Next steps](#next-steps)

## Before you start

You need the CogExPerfAgent checkout, Python 3.12 to match the container, access to the configured Elasticsearch endpoint, and a test window containing Kubernetes metrics. PerfAgent analyzes collected metrics; run your application's load test separately.

Commands below assume your terminal is in the `CogExPerfAgent` directory. The existing Desktop checkout has a Linux virtual environment; use that from WSL or create a separate Windows environment.

## 1. Prepare Python

In WSL or Linux, create a local environment if needed:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For a Windows setup that does not require activation, see [Setup](02-SETUP.md).

## 2. Configure credentials and output

For CLI collection using the current basic-authentication setting, create a local `.env` in the project root with your assigned credentials:

```dotenv
ELASTIC_USERNAME=<assigned-user>
ELASTIC_PASSWORD=<assigned-password>
```

Use actual values locally and keep `.env` out of Git. Check the Elasticsearch URL in `config/application.yaml` and the project/resource filters in `config/components.yaml`.

In `config/application.yaml`, select a writable output directory:

```yaml
collection:
  default_interval: "30s"
  output_directory: "output"
```

Use the existing `/tmp/perf-agent/output` setting when running the Linux container. This snippet replaces only the `collection` section, not the complete application configuration.

## 3. Run a known test window

Replace the example timestamps with a period when the selected components emitted metrics:

```bash
python -m app.main --entity item-CIG_DTS --start-time 2026-09-04T10:00:00Z --end-time 2026-09-04T10:30:00Z --interval 30s
```

The configured entity includes `beacon-ingress`, `dts`, `dp`, and `cis`. Add `--component dts` for a narrower first run. Times should include `Z` or an explicit offset.

## 4. Check the generated report

The terminal prints an execution ID and the final report path. With a local output root of `output`, open:

```text
output/<execution-id>/reports/item-CIG_DTS/<execution-id>_PSR_Report.html
```

Keep the execution folder intact so charts and CSV links resolve. Inspect the performance result and the number of rule checks inside the report. Process exit code 0 means generation completed; the performance result can still be FAIL or ERROR.

## 5. Use the API when you need Blob publication

The CLI generates local artifacts. The API adds background execution and publication to Azure Blob Storage. Before starting Uvicorn, supply Azure variables to its process environment; putting them only in `.env` does not configure the uploader.

See [Environment Variables](03-ENVIRONMENT-VARIABLES.md), [API Reference](11-API-REFERENCE.md), and [Blob Publication](14-AZURE-BLOB-PUBLICATION.md) for the complete API path.

## Expected completion checks

| Check | What it establishes |
| --- | --- |
| Collection reports zero failed components | Configured components completed collection requests. Review group/data coverage separately. |
| All five pipeline stages complete | Collection, normalization, summaries, charts, and HTML generation ran successfully with current settings. |
| HTML and its linked assets open | The generated artifact set can be reviewed. |
| Rule checks and values match expectations | The performance verdict has meaningful checks behind it. |
| API upload-completed message plus expected Blob files | Results were published; a 202 response alone does not establish this. |

## Next steps

- [Running PerfAgent](04-RUNNING-PERFAGENT.md) for component selection and stage reruns.
- [Configuration](05-CONFIGURATION.md) for adding entities and components.
- [Troubleshooting](08-TROUBLESHOOTING.md) if collection or reporting fails.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
