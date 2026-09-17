# MCP Integration

Document the local stdio tools and the remaining packaging and path integration work.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Table of Contents

- [Current tools](#current-tools)
- [Launch and input reference](#launch-and-input-reference)
- [Current limitations](#current-limitations)
- [Additional compatibility details](#additional-compatibility-details)
- [Next steps](#next-steps)

## Current tools

`app/mcp_server.py` exposes these FastMCP tools over stdio:

| Tool | Purpose |
| --- | --- |
| `test_connection` | Returns a simple connectivity response. |
| `list_executions` | Lists local execution directories, newest first. |
| `get_execution_summary` | Reads entity-summary CSV rows for an execution, optionally restricted to an entity. |
| `generate_entity_result` | Runs `app.main` synchronously with a 30-minute timeout and returns output excerpts. |

The MCP server currently inspects `Path.cwd() / "output"`, which differs from the configured container output root. It detects new execution folders by comparing before/after directory listings. This should be aligned with shared output configuration and explicit execution IDs before relying on it across environments or concurrent runs.

`mcp` is imported by the server but is absent from `requirements.txt`. The Docker entry point starts the HTTP API rather than the MCP server. Source presence therefore does not establish a working MCP service in the deployed image.

## Launch and input reference

With the MCP dependency installed in a separately prepared compatible environment, the source entry point is:

```bash
python -m app.mcp_server
```

Run it with the project root as the working directory. This starts a stdio transport; it is not an HTTP endpoint exposed by the Uvicorn container command. Dependency compatibility was not tested as part of this documentation update.

| Tool | Inputs |
| --- | --- |
| `test_connection` | Optional message, default `Hello`. |
| `list_executions` | Optional limit, default 20. |
| `get_execution_summary` | Execution ID and optional entity. |
| `generate_entity_result` | Entity, start time, end time, optional interval default `30s`. |

The generate tool accepts interval units `s`, `m`, and `h`, while the HTTP model also accepts `d`. Use timezone-qualified dates consistently. Its source validation is not identical to the HTTP API.

## Current limitations

MCP generation calls the CLI, so it does not automatically publish to Blob. Its result discovery compares directory listings under local `output`; align that path with pipeline output before relying on returned execution IDs. Concurrent generation can make before/after folder discovery ambiguous.

The implementation captures subprocess stdout/stderr and returns excerpts. Calling this source file successfully is a separate setup milestone from the historically deployed HTTP API.

## Additional compatibility details

The generate tool has no component selector or custom execution-ID input. Its timezone validation differs from the CLI/API: use aware timestamps for both boundaries, as mixed aware/naive inputs can fail during comparison. A subprocess success can return an empty `generated_executions` list when output is written outside the hardcoded directory. Listing order uses directory modification time, not a persisted run creation/completion timestamp.

## Next steps

- [Running PerfAgent](04-RUNNING-PERFAGENT.md) for the underlying CLI.
- [Roadmap](16-ROADMAP.md) for dependency and output-path alignment.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
