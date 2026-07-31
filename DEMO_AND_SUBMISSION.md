# Demo and Submission Guide: Lineage Fuzzer

## Devpost short description

Lineage Fuzzer is a DataHub-powered chaos-engineering agent for data reliability. It uses live
lineage, schemas, ownership, and existing assertions to constrain a deterministic semantic-fault
campaign, injects reproducible faults into an isolated fixture, measures detection coverage,
generates validated controls from DataHub schema metadata for two gaps, reruns the campaign, and
proves restoration.

## Three-minute demo target

Aim for **2 minutes 35 seconds to 2 minutes 45 seconds**.

### 0:00–0:18 — The reliability gap

Show a healthy pipeline and passing tests.

> Passing tests do not prove that the controls catch the silent failures that matter.

### 0:18–0:48 — DataHub constrains the campaign

Show lineage, schemas, ownership, and current assertions. Compile the seeded three-fault manifest
and predicted blast radius.

> DataHub tells the agent what the target can affect and which controls already exist. The
> campaign is graph-bound, versioned, and reproducible.

### 0:48–1:14 — Safety and injection

Show the sandbox markers, approval, snapshot, and three injections.

> Faults can run only against allowlisted disposable fixtures, and every mutation has a restore action.

### 1:14–1:46 — Expose the gap

Show the fault-by-control matrix: one of three caught.

> The current tests catch the null or join failure but miss a scale change and stale partition. Coverage is measured, not guessed.

### 1:46–2:17 — Select and prove controls

Show the two emitted SQL controls, validation on clean data, and execution against the faults.
Rerun the same seed and show three of three detected.

> The generator combines captured DataHub field types, the two measured gaps, and clean-profile
> boundaries into runnable SQL, validates the artifact, and proves it on the identical campaign.

### 2:17–2:36 — Restore and write back

Show matching restore checksums and the separately verified reversible DataHub assertion path.

> The fixture returns to baseline. A separate write/reread/restore exercise proves that the
> supported DataHub assertion path works without leaving test state behind.

### 2:36–2:44 — Close

> Lineage Fuzzer breaks data safely before bad data breaks production.

## Submission narrative

### Problem

Data-quality controls are usually written after incidents. Teams have no systematic way to test whether current controls detect realistic semantic failures.

### Solution

Lineage Fuzzer uses DataHub to validate a sandbox target, predict downstream impact, safely inject
faults, score detection, select validated controls for two designed gaps, rerun the campaign, and
prove complete restoration.

### What makes it original

The innovation is lineage-guided semantic fault injection and test-gap closure—not generic infrastructure chaos, anomaly monitoring, or code fuzzing.

### DataHub usage to state explicitly

- Reads lineage, schemas, owners, governance markers, and assertions.
- Uses lineage to predict blast radius for the exact sandbox target.
- Measures the assertion baseline before selecting two deterministic SQL controls.
- Separately proves a reversible custom-assertion write/result/reread/restore operation.

## Judging evidence map

| Criterion | What judges should see |
|---|---|
| Use of DataHub | Live target validation, assertion context, predicted impact, reversible assertion proof |
| Technical execution | Sandbox gate, seeded faults, restore, detection matrix, emitted SQL controls |
| Originality | Chaos engineering applied to semantic data failures via lineage |
| Real-world usefulness | Objective proof of data-quality control coverage |
| Submission quality | Dramatic before/after score, runnable examples, short repeatable demo |

## Required repository evidence

- `examples/campaign-manifest.json`
- `examples/baseline-coverage.json`
- `examples/generated/` runnable emitted controls
- `examples/final-coverage.json`
- before/after and restore checksums
- DataHub screenshots
- safety and limitations documentation

## Claims to avoid

- “Proves the data stack cannot fail.”
- “Runs safely against any production system.”
- “Replaces data observability.”
- “Generated tests are always correct.”
- “A language model writes arbitrary tests.”

Prefer: “Measures detection coverage for explicit reproducible campaigns on isolated fixtures.”

## Recording checklist

- [x] Video is public and under three minutes: <https://youtu.be/wcDgAAUbO08> (2:04).
- [ ] Sandbox protection is visible but concise.
- [ ] Campaign seed and three fault types are legible.
- [ ] Baseline and improved matrices use the same campaign.
- [ ] Emitted controls are shown executing.
- [ ] Restore proof and the separate DataHub assertion evidence are shown.
- [ ] No secrets or copyrighted music appears.
