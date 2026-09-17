# Environment Variables

Understand which settings come from YAML, local .env files, and the API process environment.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Variable reference](#variable-reference)
- [Elasticsearch authentication](#elasticsearch-authentication)
- [.env loading and subprocess behavior](#env-loading-and-subprocess-behavior)
- [Safe presence check](#safe-presence-check)
- [YAML settings and mounted configuration](#yaml-settings-and-mounted-configuration)
- [Next steps](#next-steps)

## Variable reference

| Variable | Required when | Consumed by | Notes |
| --- | --- | --- | --- |
| `ELASTIC_USERNAME` | `elastic.auth_type: basic` | Elasticsearch client | Paired with password. |
| `ELASTIC_PASSWORD` | `elastic.auth_type: basic` | Elasticsearch client | Keep the value out of source and logs. |
| `ELASTIC_API_KEY` | `elastic.auth_type: api_key` | Elasticsearch client | Sent through the API-key authorization header. |
| `AZURE_STORAGE_CONNECTION_STRING` | API publishes results | Blob uploader in the API parent process | Must be present in the Uvicorn process environment. |
| `AZURE_STORAGE_CONTAINER` | API publishes results | Blob uploader | Name of an existing container; historical deployment used `perf-insight-results`. |
| `PERF_CONFIG_DIR` | Optional readiness directory selection | `/ready` only | Does not currently redirect the pipeline's `ConfigLoader`. |
| `MPLCONFIGDIR` | Container chart rendering | Matplotlib | Dockerfile sets `/tmp/matplotlib`. |

## Elasticsearch authentication

The YAML `elastic.auth_type` supports `basic`, `api_key`, and `none`. Current configuration uses `basic` with TLS verification enabled. The URL, timeout, CA certificate option, and TLS settings come from `application.yaml`, not `ELASTIC_URL` or other inferred environment names.

For local CLI use, `.env` can contain:

```dotenv
ELASTIC_USERNAME=<assigned-user>
ELASTIC_PASSWORD=<assigned-password>
```

For API-key authentication, change the YAML setting and provide `ELASTIC_API_KEY` instead. Use your actual endpoint and access mechanism; the example values are placeholders.

## .env loading and subprocess behavior

`run_collection()` calls `load_dotenv()` inside the process executing `app.main`. This makes local `.env` credentials available to collection. Existing environment values take precedence under the current default dotenv call.

The API parent process does not call `load_dotenv()`. Changes to a subprocess environment do not propagate back to its parent. As a result, Azure values present only in `.env` can allow collection to finish while the parent uploader reports missing variables.

Supply the Azure values through your deployment secret injection or export them in the terminal that starts Uvicorn. For a local Bash session, the following prompts avoid placing the connection string in command history:

```bash
read -r -s -p 'Azure storage connection string: ' AZURE_STORAGE_CONNECTION_STRING
export AZURE_STORAGE_CONNECTION_STRING
export AZURE_STORAGE_CONTAINER=perf-insight-results
python -m uvicorn app.api:app --host 127.0.0.1 --port 8080
```

The target container name above reflects the earlier deployment; replace it when using another environment. For Windows, inject variables through your local environment or approved secret tooling before starting the process. Do not print connection-string values while diagnosing configuration.

## Safe presence check

Run this in the same environment from which the API will start. It prints only whether each variable is set:

```bash
python -c "import os; names=['ELASTIC_USERNAME','ELASTIC_PASSWORD','ELASTIC_API_KEY','AZURE_STORAGE_CONNECTION_STRING','AZURE_STORAGE_CONTAINER']; print('\n'.join(n + ': ' + ('set' if os.getenv(n) else 'missing') for n in names))"
```

Missing credentials for an unused authentication mode are expected. This command deliberately does not load `.env`, so its output reflects process environment values only.

## YAML settings and mounted configuration

Keep entity membership and metric definitions in their dedicated YAML files. The default runtime reads the project-relative `config` directory. `PERF_CONFIG_DIR=/mnt/perf-config` currently changes `/ready` without changing the pipeline configuration source.

The intended storage arrangement is Classic File Share for configuration and Blob Storage for execution artifacts. Shared config-directory resolution must be completed before using the File Share mount as the authoritative pipeline configuration.

## Next steps

- [Configuration](05-CONFIGURATION.md) for all six YAML files.
- [Blob Publication](14-AZURE-BLOB-PUBLICATION.md) for upload behavior.
- [Stratosphere Deployment](stratosphere/02-STRATOSPHERE-DEPLOYMENT.md) for storage bindings and historical evidence.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
