# API Reference

Describe the implemented HTTP endpoints, request examples, validation, and background execution behavior.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Service and endpoints](#service-and-endpoints)
- [Submit from Bash or WSL](#submit-from-bash-or-wsl)
- [Submit from PowerShell](#submit-from-powershell)
- [Validation and failure timing](#validation-and-failure-timing)
- [Operational lifecycle](#operational-lifecycle)
- [Environment requirement](#environment-requirement)
- [Next steps](#next-steps)

## Service and endpoints


Start the API with:

```shell
python -m uvicorn app.api:app --host 0.0.0.0 --port 8080
```

| Endpoint | Behavior |
| --- | --- |
| `GET /health` | Returns `{"status":"healthy"}` when the handler is reachable. |
| `GET /ready` | Returns 200 when the six config paths are files; otherwise 503 with missing filenames. Does not parse YAML or verify Elasticsearch, Blob access, or output writability. |
| `POST /runs` | Validates request shape/time ordering and returns 202 with an execution ID and `queued` status. |

Example JSON request body:

```json
{
  "entity": "item-CIG_DTS",
  "start_time": "2026-09-04T10:00:00Z",
  "end_time": "2026-09-04T10:30:00Z",
  "interval": "30s",
  "component": "dts"
}
```

Omit `component` to run all enabled members. Both timestamps must include a timezone, and start must precede end. Entity names must start with an alphanumeric character and otherwise contain alphanumerics, hyphens, or underscores. The optional interval accepts a positive integer followed by `s`, `m`, `h`, or `d`.

Example acceptance response:

```json
{
  "execution_id": "item-CIG_DTS-20260904T112414Z-408057a5",
  "status": "queued"
}
```

The response only acknowledges acceptance. Entity/component configuration resolution and external-system failures can occur afterward. Work runs through FastAPI background tasks and a subprocess; there is no durable queue, persisted run-status store, cancellation endpoint, or status polling endpoint. Check execution logs and Blob artifacts for completion. Restarting the API can interrupt accepted work.

## Submit from Bash or WSL

Once the API process has Elasticsearch access and the required Azure environment variables, submit a real test window. This example uses a local address:

```bash
curl -X POST http://127.0.0.1:8080/runs \
  -H 'Content-Type: application/json' \
  -d '{"entity":"item-CIG_DTS","start_time":"2026-09-04T10:00:00Z","end_time":"2026-09-04T10:30:00Z","interval":"30s","component":"dts"}'
```

Omit `component` for the full entity. For a deployed service, use the configured endpoint and authentication mechanism.

## Submit from PowerShell

```powershell
$requestBody = @{
    entity = 'item-CIG_DTS'
    start_time = '2026-09-04T10:00:00Z'
    end_time = '2026-09-04T10:30:00Z'
    interval = '30s'
    component = 'dts'
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8080/runs' -ContentType 'application/json' -Body $requestBody
```

## Validation and failure timing

| Condition | When it is detected |
| --- | --- |
| Missing/invalid typed input, invalid entity pattern or interval pattern | Request validation, normally HTTP 422. |
| Missing timezone or start >= end | Request handler, HTTP 422. |
| Unknown entity or component membership | Background pipeline after acceptance. |
| Missing Elasticsearch access/configuration | Background pipeline after acceptance. |
| Missing Azure variables or failed Blob access | Publication after successful pipeline completion. |

`component` is a nonempty optional string at the request model layer; actual membership is checked by collection. Clients cannot choose an execution ID through this API. The server generates an ID with a timestamp and UUID suffix.

## Operational lifecycle

```text
Request validation -> 202 queued -> background subprocess
    -> nonzero exit: log failure and stop
    -> exit 0: recursively publish execution folder
         -> upload succeeds: log file count
         -> upload fails: log error; partial blobs may remain
```

This sequence describes current code flow, not persisted run states. There is no `GET /runs/{id}`, retry, cancellation, or artifact endpoint. Application-level authentication is not implemented in `app/api.py`; deployed access policy must be handled and verified in the surrounding service setup.

## Environment requirement

The API parent does not load `.env`; Azure variables must be injected/exported before Uvicorn starts. See [Environment Variables](03-ENVIRONMENT-VARIABLES.md). Starting the service from the project root also keeps relative configuration resolution consistent.

## Next steps

- [Blob Publication](14-AZURE-BLOB-PUBLICATION.md) for completion evidence.
- [Stratosphere Deployment](stratosphere/02-STRATOSPHERE-DEPLOYMENT.md) for runtime configuration.
- [Roadmap](16-ROADMAP.md) for proposed durable lifecycle support.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
