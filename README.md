# Lineage Fuzzer

Lineage Fuzzer now includes the complete deterministic vertical slice: three sandbox-only
semantic fault adapters, lineage-predicted versus checksum-observed blast radius, a measured
1/3 baseline, a generated and validated SQL control artifact, a 3/3 rerun, verified restoration,
and a single-screen judge demo.

The live DataHub catalog/assertion read-write-re-read-restore proof remains preserved separately.
See [the judge runbook](./docs/JUDGE_DEMO.md) for the exact local commands, approval digest,
evidence map, and live-context capture flow.

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m lineage_fuzzer.demo_cli plan
$env:LINEAGE_FUZZER_INJECTION_ENABLED = "true"
.venv\Scripts\lineage-fuzzer.exe serve --host 127.0.0.1 --port 8104
```

Open `http://127.0.0.1:8104`, review the immutable digest, and approve the campaign.

## Submission title

**Lineage Fuzzer: Chaos Engineering for the Data Graph**

## Tagline

Break data safely before bad data breaks production.

## One-sentence pitch

Lineage Fuzzer reads DataHub lineage, schemas, and existing assertions to generate reversible semantic faults, injects them into isolated data fixtures, measures which controls detect them, generates missing tests, and records the improved coverage.

## Basic idea

Infrastructure teams use chaos engineering to prove that systems survive failures. Data teams mostly wait for silent semantic failures—unit changes, stale partitions, null surges, broken joins, schema drift, or missing classifications—to reach production.

Lineage Fuzzer converts the DataHub graph into an intelligent fault campaign. The agent selects high-impact fault locations, predicts the blast radius, performs reversible injections in a sandbox, observes the existing quality controls, explains gaps, generates concrete assertions or data tests, reruns the campaign, and writes coverage results back to DataHub.

## Why it can win

- **Novel combination:** Lineage-guided semantic fault injection is less crowded than generic infrastructure chaos or data observability.
- **DataHub is indispensable:** Lineage selects valuable targets and predicts affected consumers; schemas and assertions shape the tests.
- **Excellent before-and-after demo:** Detection coverage visibly improves from one of three faults to three of three.
- **Code-generation evidence:** The repository can include generated dbt tests, SQL assertions, or DataHub assertion definitions.
- **Safe implementation:** All destructive behavior is confined to disposable fixtures.

## Primary user

Data reliability engineers, analytics engineers, data platform teams, and owners of critical data products.

## Challenge category

Primary: **Agents That Do Real Work**  
Secondary: **Metadata-Aware Code Generation & Development**

## The memorable demo moment

The first campaign injects three silent faults and existing monitors catch only one. The agent uses lineage context to generate two missing tests, reruns the exact campaign, catches all three, and writes the new resilience score into DataHub.

## Name rationale

“Lineage Fuzzer” is direct, technically credible, and easy for judges to remember. The subtitle makes clear that this is data chaos engineering, not a conventional code-security fuzzer.

## Workspace map

- [Judge demo runbook](./docs/JUDGE_DEMO.md)
- [Project brief](./PROJECT_BRIEF.md)
- [Build plan](./BUILD_PLAN.md)
- [Demo and submission](./DEMO_AND_SUBMISSION.md)
- [Hackathon rules](./HACKATHON_RULES.md)
- [AI builder instructions](./AGENTS.md)

## First command for the builder

Read `AGENTS.md`, `HACKATHON_RULES.md`, and `PROJECT_BRIEF.md` completely before choosing the implementation stack or writing code.
