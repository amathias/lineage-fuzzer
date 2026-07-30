# Demo and Submission Guide: Lineage Fuzzer

## Devpost short description

Lineage Fuzzer is a DataHub-powered chaos-engineering agent for data reliability. It uses lineage, schemas, criticality, and existing assertions to design safe semantic fault campaigns, injects reproducible faults into isolated fixtures, measures detection coverage, generates missing tests, reruns the campaign, and writes the improvement back to DataHub.

## Three-minute demo target

Aim for **2 minutes 35 seconds to 2 minutes 45 seconds**.

### 0:00–0:18 — The reliability gap

Show a healthy pipeline and passing tests.

> Passing tests do not prove that the controls catch the silent failures that matter.

### 0:18–0:48 — DataHub designs the campaign

Show lineage, critical downstream consumers, schemas, and current assertions. Generate the seeded three-fault manifest and predicted blast radius.

> DataHub tells the agent where a fault matters and which controls already exist. The campaign is graph-driven, versioned, and reproducible.

### 0:48–1:14 — Safety and injection

Show the sandbox markers, approval, snapshot, and three injections.

> Faults can run only against allowlisted disposable fixtures, and every mutation has a restore action.

### 1:14–1:46 — Expose the gap

Show the fault-by-control matrix: one of three caught.

> The current tests catch the null or join failure but miss a scale change and stale partition. Coverage is measured, not guessed.

### 1:46–2:17 — Generate and prove fixes

Show generated test diffs, validation on clean data, and execution against faults. Rerun the same seed and show three of three detected.

> The agent generates runnable controls grounded in real schema and lineage, validates them, and proves the improvement using the identical campaign.

### 2:17–2:36 — Restore and write back

Show matching restore checksum and DataHub coverage/evidence update.

> The fixture returns to baseline, and DataHub now carries the resilience evidence for future engineers and agents.

### 2:36–2:44 — Close

> Lineage Fuzzer breaks data safely before bad data breaks production.

## Submission narrative

### Problem

Data-quality controls are usually written after incidents. Teams have no systematic way to test whether current controls detect realistic semantic failures.

### Solution

Lineage Fuzzer uses DataHub to choose high-value fault locations, predicts impact, safely injects faults, scores detection, generates missing tests, reruns the campaign, and records the result.

### What makes it original

The innovation is lineage-guided semantic fault injection and test-gap closure—not generic infrastructure chaos, anomaly monitoring, or code fuzzing.

### DataHub usage to state explicitly

- Reads lineage, schemas, owners, criticality, and assertions.
- Uses lineage to rank targets and predict blast radius.
- Grounds generated tests in real metadata.
- Writes supported campaign coverage/evidence context back to DataHub.

## Judging evidence map

| Criterion | What judges should see |
|---|---|
| Use of DataHub | Graph-driven target selection, assertion context, predicted impact, writeback |
| Technical execution | Sandbox gate, seeded faults, restore, detection matrix, generated tests |
| Originality | Chaos engineering applied to semantic data failures via lineage |
| Real-world usefulness | Objective proof of data-quality control coverage |
| Submission quality | Dramatic before/after score, runnable examples, short repeatable demo |

## Required repository evidence

- `examples/campaign-manifest.json`
- `examples/baseline-coverage.json`
- `examples/generated/` runnable tests
- `examples/final-coverage.json`
- before/after and restore checksums
- DataHub screenshots
- safety and limitations documentation

## Claims to avoid

- “Proves the data stack cannot fail.”
- “Runs safely against any production system.”
- “Replaces data observability.”
- “Generated tests are always correct.”

Prefer: “Measures detection coverage for explicit reproducible campaigns on isolated fixtures.”

## Recording checklist

- [x] Video is public and under three minutes: <https://youtu.be/wcDgAAUbO08> (2:04).
- [ ] Sandbox protection is visible but concise.
- [ ] Campaign seed and three fault types are legible.
- [ ] Baseline and improved matrices use the same campaign.
- [ ] Generated code is shown executing.
- [ ] Restore proof and DataHub writeback are shown.
- [ ] No secrets or copyrighted music appears.
