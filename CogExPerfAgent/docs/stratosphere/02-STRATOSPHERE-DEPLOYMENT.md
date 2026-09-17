# Stratosphere Deployment and Storage

Describe the container runtime contract, intended File Share configuration, and Azure Blob result publication.

[Project README](../../README.md) | [Documentation Index](../INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Runtime contract](#runtime-contract)
- [Storage responsibilities](#storage-responsibilities)
- [Deployment sequence](#deployment-sequence)
- [File Share migration completion criteria](#file-share-migration-completion-criteria)
- [Authentication and test triggering](#authentication-and-test-triggering)
- [Operational limitations](#operational-limitations)
- [Historical evidence and next steps](#historical-evidence-and-next-steps)

## Runtime contract

The Dockerfile at `deploy/docker/Dockerfile` installs requirements, copies `app` and `config`, switches to UID/GID 10001, and starts Uvicorn. It sets `/tmp/matplotlib` for Matplotlib and prepares `/tmp/perf-agent`.

Example local image build from the project root:

```shell
docker build -f deploy/docker/Dockerfile -t cogex-perf-agent:local-doc-check .
```

The actual Uvicorn command listens on **8080**. The Dockerfile currently declares `EXPOSE 8000`; align deployment routing with the actual listener and correct that metadata in a separate implementation change.

## Storage responsibilities

| Storage/service | Responsibility | Current status |
| --- | --- | --- |
| Git repository | Source, configuration definitions, documentation | Local implementation inspected. |
| Azure Container Registry | Built container images | Used in the historical Strato deployment. |
| Classic File Share | Intended externally mounted configuration | Migration remains incomplete; image currently includes `config`. |
| Container `/tmp/perf-agent/output` | Temporary execution workspace | Configured output root; historically verified writable on Strato. |
| Azure Blob Storage | Published execution artifacts | Uploader implemented; historical publication confirmed. |

The successful Strato troubleshooting established that the image filesystem was read-only. Directory ownership changes under `/app` could not fix writes to relative `output`; switching to `/tmp/perf-agent/output` resolved that failure. Temporary local results should not be treated as durable storage.

For the intended File Share setup, mount configuration through Strato storage mounts, for example at `/mnt/perf-config`. Complete consistent config-directory resolution across every pipeline stage before relying on `PERF_CONFIG_DIR`. Mounting files and receiving a successful readiness response alone does not demonstrate that the pipeline uses them.

## Deployment sequence

1. Prepare and identify the image using [Container Build](01-BUILD-DOCKER-IMAGE-LOCAL.md).
2. Configure the web-container route to the actual Uvicorn listener, port 8080.
3. Supply Elasticsearch credentials and Azure publication variables through the deployment's environment/secret mechanism.
4. Keep the output root on a verified writable runtime location, currently `/tmp/perf-agent/output`.
5. Check health/config-file presence, then submit a controlled test-window run.
6. Verify subprocess completion and the expected Blob artifact set.
7. Check the report's performance verdict independently of generation/publication success.

Exact Strato resource bindings depend on the active environment. The historical secret mapping used `active-connection-string` as the source for `AZURE_STORAGE_CONNECTION_STRING` and a private container named `perf-insight-results`. No secret value belongs in a repository document.

## File Share migration completion criteria

The intended configuration mount is a Classic File Share exposed through Strato `storage_mounts`, for example `/mnt/perf-config`. Code must consistently resolve that location across all stage configuration readers before the migration is complete.

Acceptance should demonstrate a mounted setting taking effect in collection, summary/chart/report generation, and output resolution. A `/ready` success is insufficient because it currently uses `PERF_CONFIG_DIR` independently of pipeline loading.

## Authentication and test triggering

The application source does not provide its own authentication middleware. Configure access through the surrounding service and verify that automated callers have the required credentials. The historical smoke-test caller lacked OAuth support; the recorded follow-up was to restore appropriate authentication and disable the temporary test Job. Current live settings were not rechecked for these guides.

## Operational limitations

Accepted background work is tied to the API process. Restart/redeployment may interrupt it, and no persisted run-status API reports recovery. Local output is temporary, partial uploads are possible, and automatic retention is not implemented in the application.

## Historical evidence and next steps

See [Build Status](../15-BUILD-STATUS.md) for the dated 4 September 2026 successful run and [Blob Publication](../14-AZURE-BLOB-PUBLICATION.md) for upload completion evidence. See [Roadmap](../16-ROADMAP.md) for durable lifecycle and configuration migration work.

---

[Project README](../../README.md) | [Documentation Index](../INDEX.md)
