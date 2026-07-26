from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lineage_fuzzer.api import create_app
from lineage_fuzzer.campaign.context import (
    ContextCaptureError,
    _direct_lineage_urns,
    context_receipt_path,
    demo_context_snapshot,
    load_live_context_snapshot,
    save_live_context_snapshot,
)
from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.fixture_contract import (
    DASHBOARD_URN,
    DEMO_LINEAGE,
    RAW_ORDERS_URN,
    STAGING_ORDERS_URN,
)
from lineage_fuzzer.demo_cli import main
from tests.live_contract import (
    CANDIDATE_SHA,
    PinnedAssertions,
    PinnedMCP,
    capture_pinned_context,
    make_settings,
    prepare_bound_runtime,
)


def _capture(workspace: Path, settings: Settings):
    return asyncio.run(capture_pinned_context(workspace, settings))


def test_capture_uses_complete_pinned_mcp_and_graphql_shapes(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    prepare_bound_runtime(tmp_path, settings)
    mcp = PinnedMCP()
    assertions = PinnedAssertions()

    context = asyncio.run(
        capture_pinned_context(
            tmp_path,
            settings,
            mcp=mcp,
            assertions=assertions,
        )
    )

    assert context.source == "datahub-mcp-live"
    assert len(context.entities) == 6
    assert len(context.lineage) == 5
    assert len(context.assertions) == 3
    assert context.provenance is not None
    assert context.provenance.candidate_sha == CANDIDATE_SHA
    assert len(context.provenance.raw_response_sha256) == 20
    assert len(mcp.calls) == 13
    assert len(assertions.calls) == 6


def test_capture_accepts_observed_alphabetical_schema_order_and_canonicalizes(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    prepare_bound_runtime(tmp_path, settings)

    context = _capture(tmp_path, settings)

    raw_customers = next(
        entity for entity in context.entities if entity["name"] == "fuzzer.raw.customers"
    )
    assert raw_customers["schemaFields"] == [
        "customer_id",
        "customer_name",
        "segment",
        "country_code",
    ]


def test_capture_ignores_governance_entities_outside_lineage_results(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    prepare_bound_runtime(tmp_path, settings)

    context = _capture(tmp_path, settings)

    assert context.lineage == DEMO_LINEAGE


def test_direct_lineage_accepts_exact_nested_nonempty_and_empty_envelopes() -> None:
    nonempty = {
        "downstreams": {
            "facets": [
                {
                    "field": "owners",
                    "aggregations": [
                        {
                            "entity": {
                                "urn": "urn:li:corpuser:lineage-fuzzer",
                                "type": "CORP_USER",
                            }
                        }
                    ],
                }
            ],
            "hasMore": False,
            "offset": 0,
            "returned": 1,
            "searchResults": [
                {
                    "degree": 1,
                    "entity": {"type": "DATASET", "urn": STAGING_ORDERS_URN},
                }
            ],
            "total": 1,
        }
    }
    empty = {
        "downstreams": {
            "facets": [],
            "hasMore": False,
            "offset": 0,
            "returned": 0,
            "searchResults": [],
            "total": 0,
        }
    }

    assert _direct_lineage_urns(nonempty, source_urn=RAW_ORDERS_URN) == (
        STAGING_ORDERS_URN,
    )
    assert _direct_lineage_urns(empty, source_urn=DASHBOARD_URN) == ()


def test_live_context_store_round_trips_with_bound_receipt(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    prepare_bound_runtime(tmp_path, settings)
    context = _capture(tmp_path, settings)
    path = tmp_path / ".lineage-fuzzer" / "campaign-context.json"

    saved = save_live_context_snapshot(path, context)
    loaded = load_live_context_snapshot(
        saved,
        settings=settings,
        workspace_root=tmp_path,
    )

    assert loaded == context
    receipt = json.loads(context_receipt_path(path).read_text(encoding="utf-8"))
    assert receipt["candidate_sha"] == CANDIDATE_SHA
    assert len(receipt["context_sha256"]) == 64
    assert "token" not in json.dumps(receipt).casefold()


def test_relabeling_local_snapshot_cannot_create_live_evidence(tmp_path: Path) -> None:
    forged = demo_context_snapshot().model_copy(update={"source": "datahub-mcp-live"})

    with pytest.raises(ContextCaptureError, match="provenance"):
        save_live_context_snapshot(tmp_path / "campaign-context.json", forged)


@pytest.mark.parametrize(
    "mcp",
    (
        PinnedMCP(incomplete_lineage=True),
        PinnedMCP(missing_schema_field=True),
        PinnedMCP(duplicate_schema_field=True),
        PinnedMCP(extra_schema_field=True),
        PinnedMCP(missing_marker=True),
        PinnedMCP(foreign_lineage=True),
        PinnedMCP(missing_lineage_degree=True),
        PinnedMCP(non_direct_lineage=True),
        PinnedMCP(duplicate_lineage=True),
        PinnedMCP(invalid_lineage_type=True),
        PinnedMCP(wrong_direction_envelope=True),
        PinnedMCP(ambiguous_lineage_envelope=True),
        PinnedMCP(malformed_lineage_envelope=True),
        PinnedMCP(top_level_lineage_envelope=True),
        PinnedMCP(paginated_lineage=True),
    ),
)
def test_capture_rejects_incomplete_or_foreign_catalog_shapes(
    tmp_path: Path,
    mcp: PinnedMCP,
) -> None:
    settings = make_settings(tmp_path)
    prepare_bound_runtime(tmp_path, settings)

    with pytest.raises(ContextCaptureError):
        asyncio.run(capture_pinned_context(tmp_path, settings, mcp=mcp))


def test_capture_rejects_missing_baseline_assertion(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    prepare_bound_runtime(tmp_path, settings)

    with pytest.raises(ContextCaptureError, match="assertions"):
        asyncio.run(
            capture_pinned_context(
                tmp_path,
                settings,
                assertions=PinnedAssertions(missing_assertion=True),
            )
        )


def test_live_context_receipt_tamper_fails_closed(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    prepare_bound_runtime(tmp_path, settings)
    path = save_live_context_snapshot(
        tmp_path / ".lineage-fuzzer" / "campaign-context.json",
        _capture(tmp_path, settings),
    )
    receipt_path = context_receipt_path(path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["fixture_sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(ContextCaptureError, match="does not match"):
        load_live_context_snapshot(path)


def test_live_context_candidate_mismatch_fails_closed(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    prepare_bound_runtime(tmp_path, settings)
    path = save_live_context_snapshot(
        tmp_path / ".lineage-fuzzer" / "campaign-context.json",
        _capture(tmp_path, settings),
    )
    wrong_candidate = settings.model_copy(update={"candidate_sha": "b" * 40})

    with pytest.raises(ContextCaptureError, match="different product candidate"):
        load_live_context_snapshot(
            path,
            settings=wrong_candidate,
            workspace_root=tmp_path,
        )


def test_hackathon_api_requires_current_live_context(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, environment="hackathon")

    app = create_app(settings=settings)
    client = TestClient(app)

    assert client.get("/").status_code == 200
    response = client.get("/api/demo/plan")
    assert response.status_code == 503
    assert "context" in response.json()["detail"].casefold()


def test_hackathon_api_exposes_only_bound_live_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(tmp_path, environment="hackathon")
    prepare_bound_runtime(tmp_path, settings)
    path = save_live_context_snapshot(
        tmp_path / ".lineage-fuzzer" / "campaign-context.json",
        _capture(tmp_path, settings),
    )
    settings = settings.model_copy(update={"campaign_context_file": path})
    monkeypatch.chdir(tmp_path)

    response = TestClient(create_app(settings=settings)).get("/api/demo/plan")

    assert response.status_code == 200
    payload = response.json()
    assert payload["context_source"] == "datahub-mcp-live"
    assert payload["run_enabled"] is True
    assert payload["candidate_sha"] == CANDIDATE_SHA
    assert len(payload["graph"]["nodes"]) == 6
    assert len(payload["graph"]["edges"]) == 5


def test_live_capture_fails_closed_without_token(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("DATAHUB_TOKEN", raising=False)

    exit_code = main(["capture-live-context"])

    output = capsys.readouterr().out
    assert exit_code == 2
    assert '"status": "blocked"' in output
    assert "DATAHUB_TOKEN is required" in output
