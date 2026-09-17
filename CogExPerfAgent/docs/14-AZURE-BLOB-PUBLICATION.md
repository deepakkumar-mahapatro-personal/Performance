# Azure Blob Publication

Publish and retrieve execution artifacts while preserving the report folder structure.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Publication behavior](#publication-behavior)
- [Blob layout](#blob-layout)
- [Prerequisites](#prerequisites)
- [Completion evidence](#completion-evidence)
- [View the report](#view-the-report)
- [Retention and reproducibility](#retention-and-reproducibility)
- [Next steps](#next-steps)

## Publication behavior


After a pipeline subprocess exits successfully, the API finds `<output-root>/<execution-id>` and recursively uploads every file. Blob names preserve relative paths under `<execution-id>/`; uploads use overwrite mode and guessed MIME types, with an octet-stream fallback. The client closes after the upload attempt.

The destination container must already exist. Missing environment variables, a missing execution directory, or an empty directory produce an upload error. Upload failures are logged; they are not exposed through a persisted run-status API. A partial upload can leave a partial execution prefix, and no completion manifest currently marks the artifact set as complete.

The historical target container was `perf-insight-results`, with Strato's `active-connection-string` secret mapped to `AZURE_STORAGE_CONNECTION_STRING`. Treat those resource bindings as deployment-specific and confirm them in the active environment.

## Blob layout

```text
<container>/
  <execution-id>/
    raw/<entity>/<component>/kubernetes.json
    aggregated/<entity>/entity-summary.csv
    aggregated/<entity>/<component>/...
    visualizations/<entity>/...
    reports/<entity>/<execution-id>_PSR_Report.html
```

The container is configured separately from the execution prefix. Blob Storage is not mounted as the pipeline's local output filesystem. Classic File Share serves the separate configuration requirement.

## Prerequisites

Supply `AZURE_STORAGE_CONNECTION_STRING` and `AZURE_STORAGE_CONTAINER` in the API process environment and verify the target container exists with appropriate access. The API parent does not load local `.env` automatically. The current uploader uses a connection string; managed-identity authentication is not implemented in this helper.

## Completion evidence

Look for the execution's subprocess exit code and the uploader's completed message with file count. Then verify expected Blob objects, including the report and linked PNG/CSV assets. Individual uploaded-object messages do not prove the full folder completed.

The uploader uses overwrite mode, but there is no dedicated HTTP retry-publication endpoint. A failed upload can leave partial results; operators currently need to investigate manually. There is no persisted completion manifest or artifact status resource.

## View the report

Use your existing authorized Azure access to download the entire execution prefix into a matching local directory structure, then open the HTML beneath `reports/<entity>`. Opening one private Blob URL does not automatically grant access to every relative asset. A future report-serving layer would need a consistent access mechanism for the complete artifact set.

## Retention and reproducibility

Runtime files under `/tmp` are temporary. The application does not define automatic local cleanup, Blob retention, or full effective-configuration snapshots. Configure a storage retention policy through the team's deployment process when required; no particular organization retention duration is claimed here.

## Next steps

- [Environment Variables](03-ENVIRONMENT-VARIABLES.md) for the parent-process environment requirement.
- [Results Processing](06-RESULTS-PROCESSING.md) for artifact responsibilities.
- [Troubleshooting](08-TROUBLESHOOTING.md) for publication failures.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
