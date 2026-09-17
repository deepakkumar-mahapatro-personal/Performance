# Documentation Index

Select a focused guide by task or follow a reading path for your role.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

## Getting started

- [Quick Start](01-QUICKSTART.md): first collection and report.
- [Setup](02-SETUP.md): environment preparation for WSL/Linux and Windows.
- [Goals and Objectives](GOALS-AND-OBJECTIVES.md): project purpose and scope.

## Configuration

- [Environment Variables](03-ENVIRONMENT-VARIABLES.md): credentials and process environment.
- [Configuration](05-CONFIGURATION.md): YAML responsibilities and adding components.
- [Performance Rules](10-PERFORMANCE-RULES.md): thresholds and outcome interpretation.

## Running and deployment

- [Running PerfAgent](04-RUNNING-PERFAGENT.md): full runs, component selection, and regeneration.
- [API Reference](11-API-REFERENCE.md): submission examples and lifecycle limits.
- [MCP Integration](13-MCP-INTEGRATION.md): local assistant tools and remaining gaps.
- [Container Build](stratosphere/01-BUILD-DOCKER-IMAGE-LOCAL.md): local image checks.
- [Stratosphere Deployment](stratosphere/02-STRATOSPHERE-DEPLOYMENT.md): runtime and storage setup.

## Data and analysis

- [Results Processing](06-RESULTS-PROCESSING.md): pipeline and artifact locations.
- [Results Details](07-RESULTS-PROCESSING-DETAILS.md): fields, metric semantics, and statistics.
- [Blob Publication](14-AZURE-BLOB-PUBLICATION.md): artifact publication and retrieval.

## Reference and help

- [Architecture](APPROACHES-AND-ARCHITECTURE.md): design and source map.
- [Troubleshooting](08-TROUBLESHOOTING.md): symptom-to-resolution guide.
- [Best Practices](09-BEST-PRACTICES.md): consistent inputs and meaningful evidence.
- [Build Status](15-BUILD-STATUS.md): implemented features and historical verification.

## Development

- [Contributing](12-CONTRIBUTING.md): extending components, metrics, and collectors.
- [Roadmap](16-ROADMAP.md): proposed priorities and completion evidence.

## Reading paths

| Audience | Suggested sequence |
| --- | --- |
| First-time user | Quick Start -> Setup if needed -> Running PerfAgent -> Results Processing. |
| Performance analyst | Configuration -> Results Details -> Performance Rules -> Best Practices. |
| Operator | Environment Variables -> API Reference -> Container Build -> Stratosphere Deployment -> Blob Publication. |
| Maintainer | Architecture -> Build Status -> Contributing -> Roadmap. |

## Quick command reference

Run from the configured project root in the prepared Python environment:

```bash
python -m app.main --help
python -m app.main --entity item-CIG_DTS --component dts --start-time 2026-09-04T10:00:00Z --end-time 2026-09-04T10:30:00Z --interval 30s
python -m uvicorn app.api:app --host 127.0.0.1 --port 8080
```

The run window is illustrative. The API command requires its own process environment for Blob publication. Detailed prerequisites and expected outcomes are in the linked guides.

## Documentation scope

This package follows the reference UXPerf documentation's modular organization while describing the inspected PerfAgent implementation. Features, deployment evidence, and proposed work are distinguished in [Build Status](15-BUILD-STATUS.md). No UXPerf-specific Playwright, Snowflake, or GitHub workflow capabilities are implied for PerfAgent.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
