# Setup Guide

Set up the project in WSL/Linux or Windows and verify local prerequisites before collection.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Locate the project](#locate-the-project)
- [WSL or Linux environment](#wsl-or-linux-environment)
- [Native Windows environment](#native-windows-environment)
- [Installed package responsibilities](#installed-package-responsibilities)
- [Configure the environment](#configure-the-environment)
- [Verify without submitting a run](#verify-without-submitting-a-run)
- [Start the local API](#start-the-local-api)
- [Next steps](#next-steps)

## Prerequisites

| Requirement | Why it is needed |
| --- | --- |
| CogExPerfAgent source checkout | Contains `app`, `config`, `requirements.txt`, and the Dockerfile. |
| Python 3.12 | Matches the current container base image. |
| Approved package-index access | Installs the packages declared in `requirements.txt`. |
| Elasticsearch network access and credentials | Required for live collection of the selected Kubernetes index. |
| Writable output folder | Used by every processing stage. |
| Azure Blob credentials and existing container | Required only for API-triggered publication. |
| Docker or the team's container runtime | Required for image build/run work, not ordinary local CLI use. |

## Locate the project

The checkout inspected for these guides is under the following WSL path:

```bash
cd /mnt/c/Users/1034061/Desktop/PerfAgent/plat-indsol-e2esolutions-engineering-psr/CogExPerfAgent
```

Its Windows equivalent is:

```powershell
Set-Location 'C:\Users\1034061\Desktop\PerfAgent\plat-indsol-e2esolutions-engineering-psr\CogExPerfAgent'
```

If your checkout differs, use your own path. Run all pipeline commands from this project directory because configuration currently defaults to relative `config`.

## WSL or Linux environment

For a new environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If the existing `venv/bin/activate` environment is valid for your WSL installation, you can activate that instead. Do not reuse a Linux virtual environment from native Windows Python.

## Native Windows environment

Create a separate environment and invoke its interpreter directly:

```powershell
py -3.12 -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-win\Scripts\python.exe -m app.main --help
```

In subsequent examples, substitute `.\.venv-win\Scripts\python.exe` for `python` when your environment is not activated. Keep `.venv-win/` in your checkout's local Git exclusion list; the existing `.gitignore` covers `.venv/` and `venv/` but does not yet list this separate Windows directory. Configure a Windows-writable output path such as `output`; the container's `/tmp/perf-agent/output` setting should not be assumed portable to native Windows.

## Installed package responsibilities

The inspected `requirements.txt` declares PyYAML, python-dotenv, requests, pytest, matplotlib, FastAPI, Uvicorn, and azure-storage-blob. YAML parsing, HTTP collection, rendering, the API, and publication depend on these packages. Most are pinned; matplotlib is unpinned.

The MCP source also imports `mcp`, which is currently absent from `requirements.txt`. Treat MCP setup as a separate incomplete packaging task; see [MCP Integration](13-MCP-INTEGRATION.md).

## Configure the environment

1. Set the Elasticsearch connection settings in `config/application.yaml`.
2. Supply the credentials corresponding to its `auth_type`.
3. Check the selected entity and its component filters.
4. Choose a writable output root.
5. For API publication, export the Azure variables before starting the API.

The configuration contract is documented in [Environment Variables](03-ENVIRONMENT-VARIABLES.md) and [Configuration](05-CONFIGURATION.md). The output root has no environment-variable override in the current implementation.

## Verify without submitting a run

```bash
python -m app.main --help
python -m py_compile app/api.py app/blob_uploader.py
python -c "from app.api import app; print(app.title)"
python -m pytest tests/test_blob_uploader.py -q
```

The API import should print `CogExPerfAgent API`. The existing uploader tests mock Azure and do not establish live connectivity. These are setup instructions, not test results from the documentation update.

## Start the local API

After setting the required process environment:

```bash
python -m uvicorn app.api:app --host 127.0.0.1 --port 8080
```

Use the following checks from another terminal:

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/ready
```

`/ready` checks configuration file presence only. It does not validate credentials, parse YAML, query Elasticsearch, or test Blob access.

## Next steps

- [Quick Start](01-QUICKSTART.md) for a first live collection.
- [Container Build](stratosphere/01-BUILD-DOCKER-IMAGE-LOCAL.md) for image packaging.
- [Troubleshooting](08-TROUBLESHOOTING.md) for environment and path problems.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
