# Build Plan: Lineage Fuzzer

## Delivery strategy

Build a fully reproducible campaign before adding more fault types. The critical proof is:

> DataHub context selects meaningful faults, the system injects them only into an isolated fixture, existing controls miss some, generated controls execute, and the identical rerun improves coverage.

## Recommended repository shape

```text
/
  app/                  # API, planning, campaign state
  web/                  # graph, campaign, coverage UI
  faults/               # safe seeded fault adapters
  generators/           # assertion/test generation and validation
  demo/                 # disposable pipeline and DataHub ingestion
  examples/             # manifests, generated tests, reports
  tests/
  docs/
  docker-compose.yml
  .env.example
  LICENSE
  README.md
```

## Phase 0: Safety harness and DataHub connection

- Pin and start open-source DataHub.
- Ingest a tiny sandbox-marked graph.
- Prove MCP/Agent Context Kit read and one supported writeback.
- Implement an allowlisted demo-target gate before any fault code.
- Add tests proving unknown hosts, schemas, and missing sandbox markers are denied.

Exit condition: a fault adapter cannot run without passing the safety gate.

## Phase 1: Build the disposable pipeline

- Create deterministic commerce data and transformations.
- Add current tests that intentionally catch only one planned fault.
- Implement snapshot, checksum, restore, and reset commands.
- Ingest full lineage, schemas, owners, criticality, and assertions into DataHub.

Exit condition: the clean pipeline and baseline controls pass, and restore returns identical checksums.

## Phase 2: Campaign model and fault library

- Define campaign, fault specification, execution result, detection, generated control, and coverage schemas.
- Implement seeded unit-scale, stale-partition, and join/null faults.
- Capture before/after evidence.
- Predict blast radius from DataHub lineage.
- Unit-test fault determinism and restoration.

Exit condition: all three faults reproduce exactly from a manifest.

## Phase 3: Detection and scoring

- Execute normal pipeline checks and assertions.
- Build a fault-by-control matrix.
- Weight scores by criticality without hiding raw counts.
- Compare predicted and observed affected assets.
- Explain why baseline controls miss two intended faults.

Exit condition: the baseline campaign produces a stable, truthful score.

## Phase 4: Generate and execute missing controls

- Use metadata-grounded templates and optionally an LLM to draft tests.
- Parse generated SQL and enforce read-only/sandbox constraints.
- Execute generated tests against clean and faulty fixtures.
- Save runnable examples under `examples/generated/`.
- Rerun the identical campaign.

Exit condition: generated controls pass clean data and detect their intended faults.

## Phase 5: DataHub writeback and UI

Write supported coverage context or evidence references back to DataHub.

Required UI:

1. Target and DataHub context.
2. Campaign manifest and predicted blast radius.
3. Safety approval.
4. Live fault/control matrix.
5. Generated test diff.
6. Before/after coverage.
7. Restoration proof and DataHub update.

Exit condition: entire demo is operable from the UI after setup.

## Phase 6: Hardening

- Add examples, screenshots, limitations, and threat model.
- Test clean setup and reset.
- Add Apache 2.0 license.
- Pin dependencies.
- Make campaign output stable enough to record repeatedly.
- Record a demo under 2:45.

## Test plan

### Unit

- Sandbox allowlist and target validation.
- Seeded fault determinism.
- Campaign schemas and manifests.
- Blast-radius traversal.
- Detection matrix and score.
- Generated code policy validation.

### Integration

- DataHub read/write.
- Snapshot/inject/run/restore per fault.
- Generated test on clean and faulty data.
- Failure during campaign still restores.

### End to end

- Seed DataHub and fixture.
- Generate campaign.
- Approve and run.
- Observe baseline gap.
- Generate controls.
- Rerun same seed.
- Verify improved coverage and restoration.
- Confirm DataHub update.

## Scope cuts if behind

Cut in this order:

1. LLM-generated fault hypotheses.
2. Column-level visualization.
3. Pull request automation.
4. More than three faults.
5. Multiple pipeline engines.

Never cut sandbox enforcement, automatic restoration, real generated-test execution, repeatable scoring, or DataHub writeback.

## Evidence to preserve

- DataHub context query and graph.
- Campaign manifest and seed.
- Before/after fault evidence.
- Detection matrix.
- Generated test diff and execution.
- Coverage delta.
- Restore checksum.
- DataHub before/after screenshot.

## Final engineering checklist

- [ ] No production target path exists.
- [ ] Seeds make all campaigns reproducible.
- [ ] Restore executes on success and failure.
- [ ] Generated code is parsed and sandboxed.
- [ ] Raw detection matrix accompanies any composite score.
- [ ] Clean-checkout setup and reset are tested.
- [ ] CI covers safety, restoration, and scoring.
- [ ] README maps proof to judging criteria.
