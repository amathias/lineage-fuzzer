# Project Brief: Lineage Fuzzer

## Product thesis

Data reliability should be tested proactively. DataHub knows which assets matter, how failures propagate, and which assertions already exist. Lineage Fuzzer uses that context to design safe fault campaigns and close observable coverage gaps.

## Problem

Data quality incidents are often silent:

- currency or unit changes preserve valid types;
- stale partitions preserve schemas;
- join-key damage changes totals without causing failures;
- null or duplicate surges remain within broad thresholds;
- a renamed or retyped column breaks downstream logic;
- sensitive-data classifications disappear.

Data teams create tests after incidents because they lack a safe, systematic way to prove which faults their controls can detect.

## MVP scenario

Create a local commerce pipeline:

1. `raw.orders`.
2. `staging.orders_clean`.
3. `marts.daily_revenue`.
4. `marts.customer_value`.
5. A simple dashboard or report artifact.
6. Baseline assertions that catch only one of three seeded faults.

Ingest lineage, schemas, owners, and existing assertions into DataHub. Mark all demo entities as sandbox-safe. Run a deterministic campaign:

- inject a 100x unit-scale change;
- create a stale partition;
- break a join key or cause a null surge.

Measure detection, generate missing tests, rerun, and reach full coverage.

## Core user journey

1. Reliability engineer selects a target or asks for a high-value campaign.
2. Agent reads DataHub lineage, schemas, ownership, criticality, and assertions.
3. Campaign planner ranks candidate faults by impact and current control coverage.
4. Safety gate confirms every target is an isolated disposable fixture.
5. Agent presents a manifest with predicted blast radius and restore procedure.
6. User approves the campaign.
7. Injector applies seeded faults and runs the normal pipeline.
8. Observer records which controls fired and compares predicted versus observed impact.
9. Agent generates missing assertions or dbt/SQL tests.
10. Validator checks generated artifacts, executes them, reruns the campaign, and records the improved score in DataHub.
11. Restorer proves the fixture returned to baseline.

## Functional requirements

### Context and campaign planning

- Query DataHub for lineage, schema fields and types, owners, domains, tags, and existing assertions.
- Rank target assets using downstream blast radius and declared criticality.
- Detect obvious assertion gaps.
- Produce a versioned, seeded campaign manifest.
- Include expected effect, affected URNs, detection expectation, time budget, and restore action for each fault.

### Fault library

Implement at least three of:

- numeric scale or unit mutation;
- null-density surge;
- duplicate-key injection;
- stale partition or timestamp shift;
- join-key corruption;
- schema rename/type drift;
- referential-integrity break;
- classification/tag removal in a test catalog scope.

Each fault must:

- run only against a clone or sandbox fixture;
- be reproducible from a seed;
- emit before/after evidence;
- include an automatic restore operation;
- avoid production credentials and targets.

### Detection and scoring

- Run existing assertions and pipeline checks.
- Attribute each detection to a specific control.
- Score detection coverage by fault and affected critical assets.
- Compare predicted and observed blast radius.
- Explain false negatives and false positives.

### Test generation

- Generate at least one runnable artifact such as a dbt schema test, SQL assertion, or supported DataHub assertion definition.
- Parse and validate generated code before running it.
- Place generated examples under `examples/generated/`.
- Execute the new control and rerun the identical seeded campaign.
- Write supported coverage/status context back to DataHub.

## Suggested architecture

```text
Campaign UI
  -> campaign API/controller
      -> DataHub context adapter
      -> target ranker + campaign planner
      -> deterministic sandbox safety gate
      -> seeded fault adapter registry
      -> pipeline/assertion runner
      -> coverage scorer
      -> test-generation and validation service
      -> restoration verifier
      -> DataHub writeback + campaign evidence store
```

Suggested stack:

- Python 3.12, FastAPI, Pydantic, NetworkX, pytest.
- React, TypeScript, Vite, lineage/campaign visualization.
- DuckDB and SQL transformations for a fast deterministic demo.
- dbt Core if setup remains reliable; otherwise generate and run standalone SQL tests while including dbt examples.
- SQLite for campaign state and receipts.
- Docker Compose for DataHub and the app.
- Optional LLM for fault hypotheses and test drafting, with deterministic templates as fallback.

## Core data contracts

### Campaign manifest

- campaign ID, seed, graph snapshot
- selected target URNs and reasons
- fault specifications
- predicted blast radius
- safety evidence and restore plan
- approval state

### Fault result

- fault ID and injected mutation
- before/after evidence
- controls executed and detections
- observed affected assets
- restore and verification receipt

### Coverage report

- baseline controls
- detection matrix
- weighted coverage score
- generated controls
- rerun matrix and score delta
- DataHub writeback receipt

## Safety model

- Require an explicit `sandbox=true` marker in application configuration and matching DataHub demo metadata.
- Deny unknown hosts, databases, or schemas.
- Use dedicated demo credentials with minimal privileges.
- Snapshot fixtures before a campaign.
- Restore in a `finally` path even when detection or generation fails.
- Verify post-restore checksums.
- Require approval before injection.

## Must-have scope

- Real DataHub graph and assertion context.
- Disposable local pipeline.
- Three fault types.
- Deterministic campaign manifest and blast-radius view.
- Safety and approval gate.
- Baseline detection matrix.
- At least one generated, validated, and executed control.
- Repeat campaign showing a score improvement.
- Automatic verified restoration.
- DataHub writeback.

## Stretch scope

- Property-based generation from schema statistics.
- Column-level lineage targeting.
- Generated pull request with test artifacts.
- Fault minimization to find the smallest escaping mutation.
- Reusable DataHub Skill for chaos-campaign generation.

## Out of scope for the MVP

- Injecting faults into production.
- Exhaustive statistical anomaly testing.
- Supporting every warehouse or observability vendor.
- Claiming that passing a finite campaign proves complete reliability.

## Acceptance criteria

- [ ] The campaign is derived from live DataHub context.
- [ ] No unmarked target can receive a fault.
- [ ] Three distinct seeded faults execute.
- [ ] Existing controls catch the intentionally designed baseline subset.
- [ ] Coverage scoring is deterministic and testable.
- [ ] At least one generated control is syntactically validated and executed.
- [ ] The identical rerun shows a measurable improvement.
- [ ] Fixtures return to matching baseline checksums.
- [ ] Results are visibly written to DataHub.
- [ ] Tests cover safety, injection, scoring, generation validation, and restoration.

## Competitive positioning

Infrastructure chaos tools and data observability products already exist. The defensible claim is:

> Lineage Fuzzer uses DataHub's graph to generate high-impact semantic data faults and prove which controls detect them.

Do not claim to invent chaos engineering or data assertions. Demonstrate why their composition through the lineage graph is new and useful.
