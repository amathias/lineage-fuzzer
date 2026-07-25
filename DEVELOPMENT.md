# Development

## Local setup

The first implementation milestone provides deterministic campaign contracts, a default-deny
safety gate, direct DataHub MCP context access, and supported custom-assertion writeback.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest
.venv\Scripts\lineage-fuzzer.exe serve
```

The API health check is available at `http://127.0.0.1:8000/api/health`.

## DataHub integration probe

With a local open-source DataHub instance running, verify the required MCP tools and GraphQL
endpoint:

```powershell
Copy-Item .env.example .env
.venv\Scripts\lineage-fuzzer.exe probe-datahub
```

The probe fails unless DataHub exposes `get_entities`, `get_lineage`, and `list_schema_fields`
through MCP and the GraphQL endpoint is reachable.

## Safety defaults

Fault injection is disabled by default. Enabling it is only one part of authorization. Every target
must also match:

- the exact local database allowlist;
- an approved manifest digest;
- an allowlisted environment and platform;
- the required DataHub sandbox marker; and
- the required DataHub sandbox tag.

## Deterministic campaign

The non-mutating plan command prints the complete manifest and the only approval digest accepted
for that context:

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m lineage_fuzzer.demo_cli plan
```

Fault injection remains disabled until explicitly enabled. For the local fixture-topology plan:

```powershell
$env:LINEAGE_FUZZER_INJECTION_ENABLED = "true"
.venv\Scripts\python.exe -m lineage_fuzzer.demo_cli `
  --artifact-root examples\generated `
  --evidence-root examples `
  run `
  --approval-sha256 b952f3635f1025b5ff7e1a64c3747c4cb4d88d3bde930f13373ebdcff8bd27cd
```

The runner restores between faults and in a final cleanup, validates observed downstream table
checksums against the fault-specific predicted URNs, executes the generated read-only SQL, and
fails unless coverage moves from exactly 1/3 to 3/3.

## Authenticated campaign context

With DataHub available and its token injected through the environment:

```powershell
.venv\Scripts\python.exe -m lineage_fuzzer.demo_cli `
  capture-live-context `
  --output .lineage-fuzzer\campaign-context.json
.venv\Scripts\python.exe -m lineage_fuzzer.demo_cli `
  --context-file .lineage-fuzzer\campaign-context.json `
  plan
```

The capture is read-only. It probes the required MCP tools, reads the exact allocated entity,
schema, downstream lineage, and assertions, rejects foreign namespace results, and writes a typed
context file atomically. Because its digest changes the manifest, print and approve the live plan
rather than reusing the offline digest.

Tests and mock transports are not accepted as demo evidence. The judge-facing campaign must retain
receipts from a running open-source DataHub instance.

