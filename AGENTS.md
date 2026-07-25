# Builder Instructions: Lineage Fuzzer

## Mission

Build a working, judge-ready vertical slice of Lineage Fuzzer: a DataHub-powered agent that safely injects semantic data faults, measures detection coverage, generates missing controls, and records the improvement.

## Read first

Before modifying code, read these files completely:

1. `HACKATHON_RULES.md`
2. `PROJECT_BRIEF.md`
3. `BUILD_PLAN.md`
4. `DEMO_AND_SUBMISSION.md`

## Non-negotiable product behavior

- Read real lineage, schemas, ownership, and assertions from open-source DataHub through an eligible integration.
- Demonstrate real DataHub writeback through a supported API or SDK.
- Restrict fault injection to disposable, explicitly marked fixtures or isolated clones.
- Support at least three genuinely different semantic fault types.
- Predict blast radius before injection and compare it with observed effects.
- Measure which existing controls detect each fault.
- Generate at least one runnable test artifact, execute it, and show improved coverage.
- Restore the fixture state after every campaign.

## Engineering principles

- Safety is a product feature: default-deny any target not marked as a sandbox.
- Use seeded randomness so the demo and tests are reproducible.
- Keep deterministic injection and scoring separate from LLM explanation and test drafting.
- Validate generated SQL or test code before execution.
- Make every campaign replayable from a manifest.
- Keep secrets in environment variables and provide `.env.example`.
- Test sandbox enforcement, restoration, fault manifests, scoring, code validation, and reruns.
- Maintain `docs/DECISIONS.md` as architectural decisions are made.

## GitHub publishing

- Canonical repository: `https://github.com/amathias/lineage-fuzzer`.
- Configured origin: `git@github-datahub-lineage-fuzzer:amathias/lineage-fuzzer.git`.
- While this chat is the project's primary writer, it may commit and intermittently push verified
  milestone changes to `origin/main`.
- Inspect the complete diff, run relevant checks, stage only intended paths, and keep
  `COORDINATOR_HANDOFF.md` current before pushing.
- Never change the remote, force push, delete remote refs, use another project's SSH alias, or add
  secrets, private keys, `.env` files, runtime receipts, or private evidence to Git.
- If `origin` is absent or differs from the exact value above, stop and escalate to the portfolio
  coordinator.

### Commit cadence

- Commit and push at coherent, verified milestones or independently reviewable sub-milestones, not
  after every edit or test run.
- Keep implementation, tests, documentation, and handoff updates for one logical change together;
  separate unrelated work.
- Use meaningful imperative Conventional Commit subjects such as `feat:`, `fix:`, `test:`, or
  `docs:`; never use `update`, `changes`, `fix stuff`, `WIP`, or `checkpoint`.
- For non-trivial changes, add a commit body covering why, key safety or compatibility decisions,
  and checks performed.
- Do not create an unverified work-in-progress commit solely because work pauses or a chat ends.

## Definition of done

A reviewer can load the demo graph, select a safe campaign, see the predicted blast radius, inject three faults, observe baseline detection coverage, generate and run missing tests, rerun the campaign at full coverage, confirm fixture restoration, and inspect DataHub writeback.

## Submission guardrails

- The repository must be public and contain an Apache 2.0 `LICENSE`.
- The work must be newly built during the submission period.
- Disclose any meaningful pre-existing code or assets.
- Keep the title independent: “Lineage Fuzzer,” described as DataHub-powered.
