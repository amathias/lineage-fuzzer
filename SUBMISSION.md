# Devpost Submission: Lineage Fuzzer

## Submission fields

**Project name:** Lineage Fuzzer

**Tagline:** Break data safely before bad data breaks production.

**Short description:** Lineage Fuzzer uses live DataHub lineage, schemas, ownership, and
assertions to plan reproducible semantic fault campaigns, measure which controls detect them,
emit validated read-only SQL controls for two designed coverage gaps, and prove complete
restoration.

**Primary challenge:** Metadata-Aware Code Generation & Development

**Devpost selection:** Metadata-Aware Code Generation & Development only

**Try the application:** [fuzzer.datahub-hackathon.aaronmathias.com](https://fuzzer.datahub-hackathon.aaronmathias.com)

**Public source:** [github.com/amathias/lineage-fuzzer](https://github.com/amathias/lineage-fuzzer)

**Public demo video:** [youtu.be/wcDgAAUbO08](https://youtu.be/wcDgAAUbO08) (2:04, English captions)

**License:** Apache License 2.0

## Inspiration

Data-quality controls are usually written after an incident. A pipeline can be green while a
currency scale changes by 100x, a partition becomes 45 days stale, or a join key quietly fills
with nulls. The types still look valid, jobs still finish, and the failure reaches a dashboard
before anyone learns that the existing tests did not cover it.

DataHub already knows which assets are connected, who owns them, and which assertions exist.
Lineage Fuzzer turns that context into a proactive reliability exercise: break an isolated copy
on purpose, measure the controls, close the gaps, and restore everything.

## What it does

Lineage Fuzzer runs one deterministic, approval-bound campaign:

1. It captures an exact six-dataset commerce graph from live open-source DataHub.
2. It validates complete schemas, five lineage edges, ownership, domain, project and sandbox
   tags, the `sandbox=true` marker, and three active custom assertions.
3. It uses that graph to predict the downstream blast radius of faults against
   `fuzzer.raw.orders`.
4. It snapshots a disposable DuckDB fixture and injects three different semantic failures:
   a 100x amount-scale change, a 45-day stale partition, and a 10% customer-key null surge.
5. It compares predicted versus observed changed-table checksums and measures the controls
   actually captured from DataHub.
6. The baseline detects 1 of 3 faults. The agent generates two validated, runnable, read-only SQL
   controls from the captured DataHub schema, the measured gaps, and a clean-data profile, then
   executes them and reruns the identical seeded campaign.
7. Coverage improves from 33.3% to 100%, every predicted blast radius matches the observed
   effects, and all six fixture checksums return to baseline.
8. The manifest, context digest, matrices, emitted SQL, replay digest, and restoration proof
   are stored as immutable evidence.

The result is deliberately narrower and more useful than a generic “AI data tester”: it proves
detection coverage for explicit semantic failures on one isolated fixture. It does not claim
that a finite campaign proves an entire production stack is reliable.

## How I use DataHub

DataHub is the campaign's source of truth, not a decorative catalog lookup.

- The eligible DataHub MCP integration uses the pinned MCP client and the `get_entities`,
  `list_schema_fields`, and `get_lineage` tools to capture the six exact datasets, schemas, and
  one-hop downstream graph from self-hosted open-source DataHub.
- Supported DataHub GraphQL operations read the custom assertions attached to each relevant
  dataset. Live campaign execution derives its baseline controls from those exact assertion URNs
  and definitions; a local fixture cannot become “live” by changing a label.
- Supported DataHub OpenAPI aspect operations provision and positively verify the allowlisted
  sandbox catalog. Approval-bound reset can tombstone only the six exact datasets and three exact
  baseline assertions, then verify each status directly.
- A separate live proof used the supported assertion APIs to create and activate one custom
  assertion, report a fixed result, re-read it, and restore it by verified soft deletion.

The live snapshot is bound to verified catalog state, DataHub tool schemas, raw-response digests,
and current fixture checksums. In hackathon mode, stale or incomplete context makes readiness fail
and disables the public Run button.

## Architecture

| Layer | Role |
|---|---|
| Open-source DataHub | Six sandbox datasets, five lineage edges, complete schemas and governance metadata, three baseline assertions |
| DataHub MCP Server | Eligible live context integration for entities, schema fields, and direct lineage |
| DataHub GraphQL and OpenAPI | Assertion discovery, bounded catalog lifecycle, and the separate restored writeback proof |
| Deterministic planner | Seeded manifest, exact target, predicted blast radius, restore actions, and approval digest |
| Safety gate | Default-deny checks for environment, platform, path, URN prefix, identity, tags, marker, and manifest approval |
| DuckDB fault adapters | Reproducible numeric-scale, partition-staleness, and null-density mutations against one disposable fixture |
| Observer and scorer | Table-checksum blast comparison and fault-by-control coverage matrix |
| SQL control builder and validator | Two deterministic read-only controls restricted to the approved fixture table |
| Evidence store | Immutable manifest/context-digest run directories; byte-different replays cannot overwrite evidence |
| FastAPI judge UI | Live-context gate, graph and fault plan, single-flight execution, before/after coverage, artifact hash, and restoration result |

The core stack is Python, FastAPI, Pydantic, DuckDB, DataHub MCP Server, DataHub GraphQL/OpenAPI,
and a small dependency-free browser UI. Campaign logic is deterministic; no paid model or API is
required to reproduce the result.

## Safety model

Safety is part of the product:

- The only mutable physical target is the repository's disposable Lineage Fuzzer DuckDB fixture.
- Only the exact `fuzzer.*` namespace on DuckDB/DEV is accepted.
- The target must have the exact Lineage Fuzzer owner, domain, project tag, sandbox tag, and
  `sandbox=true` property captured from DataHub.
- Injection is disabled by default and requires the exact context-bound manifest digest.
- Only one campaign can run at a time.
- Every fault restores in a `finally` path, restoration is checked after each fault, and the
  campaign succeeds only if the final six-table checksums match the baseline.
- The emitted SQL artifact must be one read-only statement and may reference only the approved
  table.
- Catalog reset is an exact allowlist, never a search delete or global cleanup.

Production databases and unmarked assets are rejected. The campaign never injects faulty rows
into DataHub or into a production warehouse.

## Intended users and adoption

The initial users are analytics engineers, data platform teams, and reliability engineers who
need evidence that their current controls catch silent semantic failures.

Judges can use the hosted application without local setup:
[open the live judge UI](https://fuzzer.datahub-hackathon.aaronmathias.com), confirm
`datahub-mcp-live`, review the graph and three-fault manifest, and approve the exact campaign.

For local evaluation from the [public repository](https://github.com/amathias/lineage-fuzzer):

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,datahub]"
.venv\Scripts\python.exe -m lineage_fuzzer.pipeline_cli seed
$env:LINEAGE_FUZZER_INJECTION_ENABLED = "true"
.venv\Scripts\lineage-fuzzer.exe serve --host 127.0.0.1 --port 8104
```

macOS/Linux equivalent:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,datahub]'
.venv/bin/python -m lineage_fuzzer.pipeline_cli seed
export LINEAGE_FUZZER_INJECTION_ENABLED=true
.venv/bin/lineage-fuzzer serve --host 127.0.0.1 --port 8104
```

That local flow is intentionally labeled `local-fixture-topology`; it is useful for development
but is not presented as live DataHub evidence. Connecting another deployment requires an
open-source DataHub instance, the supported MCP endpoint, a least-privilege runtime credential,
and an explicitly allocated sandbox catalog. Complete verification and archive commands are in
the repository README.

## Challenges

### Treating metadata as a strict contract

Real MCP responses included schema fields in a different non-semantic order, governance entities
inside lineage facets, and two exact downstream envelope shapes for nonempty and empty results.
I tightened parsers around the pinned response locations while continuing to reject duplicates,
foreign URNs, pagination, missing fields, contradictory metadata, and ambiguous envelopes.

### Distinguishing product failures from infrastructure failures

An approval-bound reset completed all writes but its old verifier traversed GraphQL through
tombstoned datasets. I replaced that verification with exact direct status reads and proved an
idempotent zero-write recovery. Later, shared search failures were traced to an OpenSearch process
outage; after the backend recovered, the unchanged seed and live capture succeeded. The product
continued to fail closed rather than converting unavailable search into false success.

### Making a destructive-looking demo genuinely safe

Every fault is deterministic and reversible, but that is not enough. I bound the target through
DataHub metadata, a physical path allowlist, a manifest approval, single-flight execution, and
checksum verification. Evidence is content-addressed so a rerun cannot rewrite history.

### Emitting control code that can be trusted

The deterministic generator compiles the amount-scale and staleness gaps into typed control
specifications using captured DataHub field names and types plus clean-profile boundaries. Each
control is generated only after the gap is measured, must parse as one read-only statement, may
reference only the approved table, must pass against clean data, and must detect its intended fault
before it counts toward improved coverage.

## Accomplishments

- Built a complete six-entity, five-edge live DataHub contract with schemas, governance metadata,
  and persistent baseline assertions.
- Implemented three genuinely different, seeded semantic fault adapters.
- Matched predicted and observed blast radius for every fault.
- Measured an honest baseline of 1/3 and proved 3/3 with emitted executable SQL controls.
- Restored the fixture between every fault and verified all six final table checksums.
- Preserved immutable replay evidence and rejected byte-different overwrites.
- Proved a bounded DataHub assertion write/result/re-read/restore transaction without changing
  foreign project state.
- Shipped a public, live-context-gated judge experience and a reproducible Apache-2.0 repository.

## What I learned

Metadata-aware agents are strongest when metadata is executable policy. The same lineage that
predicts business impact can constrain a fault target; the same assertions that describe current
quality can become a measurable coverage baseline; and provenance can prevent a stale snapshot
from authorizing a new mutation.

I also learned that “restore” is not one operation. It needs a snapshot, an unconditional path,
positive postconditions, idempotent recovery, and evidence that neighboring namespaces did not
change.

## What's next

- Add more adapters, including duplicate keys, schema drift, and referential-integrity breaks.
- Use column-level lineage and criticality to rank a larger set of candidate campaigns.
- Emit merge-ready dbt tests alongside the standalone SQL artifact.
- Add dynamic, metadata-grounded control synthesis and a review workflow for promoting approved
  controls into governed DataHub assertions.
- Generalize the strict fixture contract into reusable per-team sandbox policies without
  weakening the default-deny boundary.

## Verified evidence boundary

Public-environment verification captured six entities, five lineage edges, three baseline
assertions, sibling-project isolation, readiness 200, and a plan reporting live DataHub MCP context
with execution enabled. A complete campaign separately proved 1/3 baseline coverage, 3/3 coverage
with the two emitted controls, and full fixture restoration. A separate reversible assertion
write/result/reread/restore exercise proved the supported DataHub write path and removed the test
assertion afterward. These are distinct evidence boundaries and are not presented as one execution.

Fault mutations occur only in the isolated DuckDB fixture. DataHub receives only the separately
approved catalog and assertion operations described above. No production target, credential,
private receipt, or coordinator evidence directory is part of the public submission.
