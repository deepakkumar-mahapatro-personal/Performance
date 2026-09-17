# Build the Docker Image Locally

Build and inspect the existing PerfAgent API image using the project Dockerfile.

[Project README](../../README.md) | [Documentation Index](../INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Required tools and context](#required-tools-and-context)
- [Dockerfile behavior](#dockerfile-behavior)
- [1. Verify imports before building](#1-verify-imports-before-building)
- [2. Build a versioned image](#2-build-a-versioned-image)
- [3. Start a local container](#3-start-a-local-container)
- [4. Check the service and a controlled run](#4-check-the-service-and-a-controlled-run)
- [Registry and deployment handoff](#registry-and-deployment-handoff)

## Required tools and context

Use Docker or the team's installed compatible container runtime. Run the build from the `CogExPerfAgent` project directory, where `requirements.txt`, `app`, and `config` are available. The reference UXPerf repository's build scripts are specific to that application and are not part of PerfAgent.

## Dockerfile behavior

| Setting | Current value |
| --- | --- |
| Base image | `python:3.12-slim` |
| Working directory | `/app` |
| Runtime user | UID/GID 10001 |
| Copied application content | `app`, `config`, installed requirements. |
| Matplotlib writable configuration | `/tmp/matplotlib` |
| API listener | `0.0.0.0:8080` |
| Declared EXPOSE metadata | 8000; currently differs from the listener. |

`.dockerignore` excludes local secrets, virtual environments, runtime outputs/logs, tests, docs, and Git metadata from the build context. `requirements.txt` currently lacks the optional MCP dependency; the image's entry point is the HTTP API.

## 1. Verify imports before building

In a prepared environment:

```bash
python -m py_compile app/api.py app/blob_uploader.py
python -c "from app.api import app; print(app.title)"
python -m pytest tests/test_blob_uploader.py -q
```

These checks help detect syntax/import regressions such as the indentation issue encountered in the earlier deployment. They do not verify live Elasticsearch or Azure access.

## 2. Build a versioned image

```bash
docker build -f deploy/docker/Dockerfile -t cogex-perf-agent:local-doc-check .
```

Use a unique release tag when preparing a deployment so the image can be identified unambiguously. Preserve the container output configuration `/tmp/perf-agent/output` when building for Strato.

## 3. Start a local container

With the required variables already exported in the host shell:

```bash
docker run --rm --name perfagent-local -p 127.0.0.1:8080:8080 \
  -e ELASTIC_USERNAME -e ELASTIC_PASSWORD \
  -e AZURE_STORAGE_CONNECTION_STRING -e AZURE_STORAGE_CONTAINER \
  cogex-perf-agent:local-doc-check
```

This example matches the current basic-authentication configuration. For API-key authentication, adjust YAML and pass `ELASTIC_API_KEY`. The mapping uses 8080 because it is the actual listener.

## 4. Check the service and a controlled run

Use `/health` and `/ready`, then follow [API Reference](../11-API-REFERENCE.md) to submit a known test window. Verify logs, output, report verdict, and Blob publication separately. Local files disappear when this temporary container is removed; published Blob artifacts are the durable result path in the current design.

## Registry and deployment handoff

Tag and publish through the team's authenticated Container Registry workflow, recording the image reference and source revision. The earlier deployment used `nerdctl` and Azure Container Registry; these guides do not claim a PerfAgent-specific automated GitHub image workflow exists. See [Stratosphere Deployment](02-STRATOSPHERE-DEPLOYMENT.md) for the verified runtime constraints.

---

[Project README](../../README.md) | [Documentation Index](../INDEX.md)
