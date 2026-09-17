# Roadmap

Prioritize follow-up work using explicit completion evidence.

[Project README](../README.md) | [Documentation Index](INDEX.md)

**Last updated:** 7 September 2026 | **Basis:** inspected PerfAgent working tree; historical deployment evidence is dated separately.

These are proposed follow-ups, not implemented capabilities or delivery commitments.

| Priority | Work | Completion evidence |
| --- | --- | --- |
| 1 | Complete shared configuration-directory resolution and File Share migration | Every stage uses mounted configuration; a changed mounted setting is reflected in a run. |
| 1 | Confirm production authentication and retire temporary test triggering | Authorized callers can run the service; deployment test artifacts are removed or disabled as intended. |
| 1 | Persist run lifecycle and upload outcome | Execution ID exposes queued/running/succeeded/failed states and artifact publication state. |
| 1 | Address interrupted/partial runs | Durable execution strategy, bounded concurrency, timeout policy, and explicit complete/partial artifact metadata. |
| 2 | Align configuration behavior | Table switches, filenames, MCP paths, and container port metadata match documented settings. |
| 2 | Expand meaningful automated coverage | Tests cover query boundaries/group completeness, normalization, statistics, missing data, rule semantics, and API failure lifecycle. |
| 2 | Define real acceptance criteria | Owners approve thresholds and distinguish maximum observed replicas from continuous availability requirements. |
| 2 | Improve reproducibility and retention | Runs capture source version, effective configuration without secrets, timestamps, outcome, and artifact retention policy. |
| 3 | Extend Elasticsearch collectors | Implement and register additional collectors/normalizers for approved transaction, SQL, Kafka, or APM needs. |
| 3 | Add LLM-assisted analysis | Implement an analyzer and define its inputs, evidence references, and relationship to deterministic rules. |

## Implementation notes

Configuration directory work should cover collection, downstream stage config readers, readiness, output resolution, and MCP consumers together. Run lifecycle work should distinguish processing outcome, performance verdict, and publication outcome.

Data-quality follow-ups should cover group truncation, missing metric coverage, empty histogram buckets in replica counts, and zero-check PASS behavior. These are separate from confirming the historical successful run.

## Next steps

- [Build Status](15-BUILD-STATUS.md) for the current evidence.
- [Architecture](APPROACHES-AND-ARCHITECTURE.md) for affected modules.

---

[Project README](../README.md) | [Documentation Index](INDEX.md)
