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

Tests and mock transports are not accepted as demo evidence. The judge-facing campaign must retain
receipts from a running open-source DataHub instance.

