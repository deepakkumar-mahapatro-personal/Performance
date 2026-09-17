# Troubleshooting Guide

Diagnose setup, collection, reporting, API, and publication problems using concrete evidence.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Quick diagnosis](#quick-diagnosis)
- [Issue: Blob upload reports missing credentials after collection succeeds](#issue-blob-upload-reports-missing-credentials-after-collection-succeeds)
- [Issue: Component count looks correct but availability is uncertain](#issue-component-count-looks-correct-but-availability-is-uncertain)
- [Issue: API container fails during startup](#issue-api-container-fails-during-startup)
- [Issue: Report shows ERROR](#issue-report-shows-error)
- [Information to include in an issue](#information-to-include-in-an-issue)
- [Next steps](#next-steps)

## Quick diagnosis

| Symptom | Interpretation and next check |
| --- | --- |
| Read-only filesystem error for `output` | Verify the runtime output root is writable and does not resolve below `/app`. |
| `/ready` returns 503 | Check its reported config directory and the six required files; then check the directory actually used by the pipeline. |
| `/ready` succeeds but collection fails | Readiness only checks file existence; inspect YAML validity, credentials, connectivity, and source filters. |
| `/runs` returns 202 but results are absent | Check later subprocess and upload logs using the execution ID; acceptance is not completion. |
| Local report exists but Blob artifacts are missing | Check upload logs, both Azure environment variables, the existing target container, and access. |
| Report has missing charts after download | Preserve the execution folder hierarchy and retrieve referenced PNG files. |
| MCP cannot find a known run | Compare its hardcoded local `output` directory with the configured pipeline output root. |
| API is unreachable through container routing | Uvicorn listens on 8080; Dockerfile EXPOSE currently says 8000. |
| HTTP redirect when a test Job calls the service | Historical deployment encountered an authentication integration issue; configure caller credentials and the service's authentication policy together. |
| Unexpectedly sparse results | Review time window, project/resource/container filters, exclusions, metric field availability, and the 100-group aggregation limit. |
| Process succeeded but report says FAIL | Pipeline completion and performance rule results are separate outcomes. |

## Issue: Blob upload reports missing credentials after collection succeeds

**Symptoms:** API logs show subprocess exit code 0 followed by a missing Azure environment-variable error.

**Cause:** `.env` is loaded inside collection, but the uploader runs in the API parent process. Subprocess environment changes do not configure the parent.

**Resolution:** Inject the Azure connection string and container into the environment before starting Uvicorn. Restart the API under that configured environment, then submit a new run. The existing API has no standalone retry-upload endpoint.

## Issue: Component count looks correct but availability is uncertain

**Symptoms:** `replica_count` is positive while some metrics are missing.

**Cause:** Replica counting uses normalized pod names at timestamps without checking `has_data` or bucket document count. Empty buckets can count.

**Resolution:** Inspect raw response bucket counts and normalized `has_data`. Use a separate availability criterion if continuous presence matters; the current sample replica rule does not provide it.

## Issue: API container fails during startup

**Symptoms:** Uvicorn cannot import `app.api`, or the container exits before accepting requests.

**Resolution:** In the intended Python environment, run module compilation and an application import:

```bash
python -m py_compile app/api.py app/blob_uploader.py
python -c "from app.api import app; print(app.title)"
```

The earlier deployment encountered an indentation error at import time. Missing installed dependencies can produce a similar startup failure category. Validate the exact image being released.

## Issue: Report shows ERROR

**Symptoms:** HTML exists and the pipeline may exit 0, but rule evaluation is marked ERROR.

**Cause:** The HTML builder surfaces rule configuration/evaluation errors inside the report.

**Resolution:** Check `rules.yaml` syntax, selected statistics/operators, and readable metric names against `entity-summary.csv`. Regenerate the report after correcting the configuration. Do not treat process completion as a passing performance check.

## Information to include in an issue

Record execution ID, entity/component, timezone-qualified test window, interval, source revision, environment type, failed stage, redacted error, and which artifacts exist. Include relevant nonsecret configuration keys and a small example of unexpected values. Do not attach `.env` or credential-bearing output.

## Next steps

- [Setup](02-SETUP.md) for environment preparation.
- [Build Status](15-BUILD-STATUS.md) for known incomplete features.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
