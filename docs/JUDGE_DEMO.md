# Judge Demo

Lineage Fuzzer runs one immutable, seeded campaign against the disposable DuckDB fixture. The
campaign mutates only `fuzzer.raw.orders`, restores the fixture between every fault, and performs
a final six-table checksum comparison before it can return `proved_and_restored`.

## Ninety-second story

1. Open the app and point out the preserved live DataHub proof: authenticated catalog read,
   custom-assertion write and result, re-read, restore, readiness 200, and foreign-project
   isolation.
2. Show the immutable campaign SHA-256 and the three seeded faults:
   100x order amounts, 45-day stale partitions, and a 10% customer-key null surge.
3. Approve and run the exact digest.
4. Show that every fault's observed downstream checksums match its lineage-predicted blast radius.
5. Show baseline coverage at 1/3: the existing not-null control detects only the null surge.
6. Open the generated read-only SQL artifact. It adds amount-range and partition-freshness checks.
7. Show improved coverage at 3/3 and the final restoration verification.

## Local judge flow

Install and verify:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
```

Print the plan before enabling mutation:

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m lineage_fuzzer.demo_cli plan
```

For this candidate, the offline fixture-topology approval SHA-256 is:

```text
b952f3635f1025b5ff7e1a64c3747c4cb4d88d3bde930f13373ebdcff8bd27cd
```

Run the local campaign and retain its sanitized evidence:

```powershell
$env:LINEAGE_FUZZER_INJECTION_ENABLED = "true"
.venv\Scripts\python.exe -m lineage_fuzzer.demo_cli `
  --artifact-root examples\generated `
  --evidence-root examples `
  run `
  --approval-sha256 b952f3635f1025b5ff7e1a64c3747c4cb4d88d3bde930f13373ebdcff8bd27cd `
  --approved-by judge-demo
```

Run the browser UI:

```powershell
$env:LINEAGE_FUZZER_INJECTION_ENABLED = "true"
.venv\Scripts\lineage-fuzzer.exe serve --host 127.0.0.1 --port 8104
```

Open `http://127.0.0.1:8104`. The button submits the exact displayed plan digest. Injection
remains disabled unless the environment flag is set, and every other safety check still applies.

## Live DataHub context mode

The local example intentionally identifies its context as `local-fixture-topology`. When a real
DataHub instance is available, capture the allocated context without printing the token:

```powershell
.venv\Scripts\python.exe -m lineage_fuzzer.demo_cli `
  capture-live-context `
  --output .lineage-fuzzer\campaign-context.json
```

The command requires `DATAHUB_TOKEN`, probes the required MCP tools, and then calls:

- `get_entities` for the exact allocated dataset URN;
- `list_schema_fields` for the target schema;
- `get_lineage` downstream for three hops; and
- the authenticated GraphQL dataset-assertions query.

Every returned dataset must remain inside the configured platform, environment, and `fuzzer.`
URN prefix. The saved file must contain lineage and is marked `datahub-mcp-live`. Use it for the
plan, campaign, and API:

```powershell
.venv\Scripts\python.exe -m lineage_fuzzer.demo_cli `
  --context-file .lineage-fuzzer\campaign-context.json `
  plan
$env:LINEAGE_FUZZER_CONTEXT_FILE = ".lineage-fuzzer\campaign-context.json"
```

Because the context digest is part of the immutable manifest, live capture produces its own
approval SHA-256. Never reuse the offline digest for a live-context plan.

## Evidence map

| File | What it proves |
|---|---|
| `examples/campaign-manifest.json` | Seed, exact target, three fault specifications, and predicted URNs |
| `examples/baseline-coverage.json` | Existing controls detect one of three independent faults |
| `examples/generated/lineage_fuzzer_generated_controls.sql` | Generated, validated, runnable read-only SQL |
| `examples/final-coverage.json` | Existing plus generated controls detect all three faults |
| `examples/campaign-report.json` | Approval, mutation hashes, exact blast comparison, replay digest, and restoration |

The committed local report has replay SHA-256
`5e7c9171bcfc0f24d3165711b5690f74a6ad3eb69e73b54187d0bb26cc1fa9f4`.
The older live DataHub proof remains separate, immutable coordinator evidence; its receipt hashes
- Campaign execution is single-flight per app process; a concurrent run fails with HTTP 409.
and isolation result are recorded in `COORDINATOR_HANDOFF.md`.

## Honest boundaries

- No production database is accepted; only the exact allowlisted repository fixture is mutable.
- Local committed campaign evidence is not represented as a new live DataHub receipt.
- The completed live assertion proof is preserved and was not rerun for this milestone.
- LLM output cannot authorize mutation or execute unvalidated SQL.
- The generated artifact is deterministic application output grounded in schema and measured
  control gaps.
