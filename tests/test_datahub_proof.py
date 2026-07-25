from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lineage_fuzzer.allocation import AllocationViolation
from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.fixture_catalog import (
    DATASET_URN,
    DOMAIN_URN,
    PROJECT_TAG_URN,
    SANDBOX_TAG_URN,
)
from lineage_fuzzer.datahub.proof import (
    ASSERTION_URN,
    DEFAULT_PROOF_PLAN,
    DataHubAssertionProofService,
    ProofApprovalViolation,
    ProofVerificationError,
)
from lineage_fuzzer.datahub.protocols import WritebackReceipt


def _settings(workspace: Path) -> Settings:
    fixture_root = workspace / "demo" / "fixtures" / "lineage-fuzzer"
    state_dir = workspace / ".lineage-fuzzer"
    state_dir.mkdir()
    return Settings(
        PROJECT_SLUG="lineage-fuzzer",
        APP_STATE_DIR=state_dir,
        DEMO_FIXTURE_ROOT=fixture_root,
        LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS=str(
            fixture_root / "lineage_fuzzer.duckdb"
        ),
        DATAHUB_DOMAIN="Demo / Lineage Fuzzer",
        DATAHUB_PROJECT_TAG="project-lineage-fuzzer",
        DATAHUB_URN_PREFIX="fuzzer.",
    )


class FakeProofClients:
    def __init__(
        self,
        *,
        wrong_result: bool = False,
        missing_marker: bool = False,
    ) -> None:
        self.active = False
        self.created = False
        self.result: dict[str, Any] | None = None
        self.calls: list[tuple[str, Any]] = []
        self.wrong_result = wrong_result
        self.missing_marker = missing_marker

    async def get_entity(self, **request: Any) -> Any:
        self.calls.append(("catalog_read", request))
        custom_properties = (
            {"project_slug": "lineage-fuzzer"}
            if self.missing_marker
            else {"sandbox": "true", "project_slug": "lineage-fuzzer"}
        )
        return [
            {
                "urn": DATASET_URN,
                "datasetProperties": {"value": {"customProperties": custom_properties}},
                "globalTags": {
                    "value": {
                        "tags": [
                            {"tag": PROJECT_TAG_URN},
                            {"tag": SANDBOX_TAG_URN},
                        ]
                    }
                },
                "domains": {"value": {"domains": [DOMAIN_URN]}},
                "status": {"value": {"removed": False}},
            }
        ]

    async def assertions_for_dataset(self, dataset_urn: str) -> dict[str, Any]:
        self.calls.append(("read", dataset_urn))
        assertions: list[dict[str, Any]] = []
        if self.active:
            plan = DEFAULT_PROOF_PLAN
            result_type = "FAILURE" if self.wrong_result else plan.result_type
            assertions.append(
                {
                    "urn": plan.assertion_urn,
                    "info": {
                        "customType": plan.assertion_type,
                        "customAssertion": {"entityUrn": plan.dataset_urn},
                    },
                    "runEvents": {
                        "runEvents": [
                            {
                                "timestampMillis": plan.timestamp_millis,
                                "result": {
                                    "type": result_type,
                                    "nativeResults": [
                                        {"key": key, "value": value}
                                        for key, value in plan.properties
                                    ],
                                },
                            }
                        ]
                    },
                }
            )
        return {"dataset": {"assertions": {"assertions": assertions}}}

    async def upsert_custom_assertion(self, **values: Any) -> WritebackReceipt:
        self.calls.append(("upsert", values))
        self.created = True
        return WritebackReceipt(
            operation="upsert_custom_assertion",
            entity_urn=values["assertion_urn"],
            response={},
        )

    async def report_assertion_result(self, **values: Any) -> WritebackReceipt:
        self.calls.append(("result", values))
        self.result = values
        return WritebackReceipt(
            operation="report_assertion_result",
            entity_urn=values["assertion_urn"],
            response={},
        )

    async def set_soft_deleted(self, **values: Any) -> dict[str, Any]:
        self.calls.append(("status", values))
        assert values["entity_type"] == "assertion"
        assert values["entity_urn"] == ASSERTION_URN
        self.active = not values["removed"]
        return {"ok": True}


@pytest.mark.asyncio
async def test_proof_writes_rereads_restores_and_persists_four_receipts(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    clients = FakeProofClients()
    service = DataHubAssertionProofService(
        settings,
        clients,
        clients,
        workspace_root=tmp_path,
    )

    result = await service.run(approval_sha256=DEFAULT_PROOF_PLAN.sha256)

    assert result["status"] == "proved_and_restored"
    assert clients.created is True
    assert clients.active is False
    assert clients.result is not None
    assert clients.result["timestamp_millis"] == DEFAULT_PROOF_PLAN.timestamp_millis
    assert set(result["receipt_paths"]) == {"before", "write", "after", "restore"}
    for path_value in result["receipt_paths"].values():
        receipt = Path(path_value)
        assert receipt.is_file()
        content = receipt.read_text(encoding="utf-8").casefold()
        assert "authorization" not in content
        assert "bearer" not in content
        assert "not-a-real-token" not in content


@pytest.mark.asyncio
async def test_proof_rejects_missing_approval_before_network(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    clients = FakeProofClients()
    service = DataHubAssertionProofService(
        settings,
        clients,
        clients,
        workspace_root=tmp_path,
    )

    with pytest.raises(ProofApprovalViolation, match="approval SHA-256"):
        await service.run(approval_sha256="wrong")

    assert clients.calls == []


@pytest.mark.asyncio
async def test_proof_rejects_foreign_assertion_before_network(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    clients = FakeProofClients()
    foreign = DEFAULT_PROOF_PLAN.model_copy(
        update={"assertion_urn": "urn:li:assertion:other.catalog-proof"}
    )
    service = DataHubAssertionProofService(
        settings,
        clients,
        clients,
        workspace_root=tmp_path,
        plan=foreign,
    )

    with pytest.raises(AllocationViolation):
        await service.run(approval_sha256=foreign.sha256)

    assert clients.calls == []


@pytest.mark.asyncio
async def test_proof_restores_when_reread_does_not_match_plan(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    clients = FakeProofClients(wrong_result=True)
    service = DataHubAssertionProofService(
        settings,
        clients,
        clients,
        workspace_root=tmp_path,
    )

    with pytest.raises(ProofVerificationError, match="result"):
        await service.run(approval_sha256=DEFAULT_PROOF_PLAN.sha256)

    assert clients.active is False
    restore = (
        settings.state_dir
        / "datahub-receipts"
        / f"assertion-{DEFAULT_PROOF_PLAN.sha256[:16]}"
        / "restore.json"
    )
    assert restore.is_file()


@pytest.mark.asyncio
async def test_proof_rejects_missing_catalog_marker_before_mutation(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    clients = FakeProofClients(missing_marker=True)
    service = DataHubAssertionProofService(
        settings,
        clients,
        clients,
        workspace_root=tmp_path,
    )

    with pytest.raises(AllocationViolation, match="required dataset aspects"):
        await service.run(approval_sha256=DEFAULT_PROOF_PLAN.sha256)

    assert [call[0] for call in clients.calls] == ["catalog_read"]


@pytest.mark.asyncio
async def test_reset_is_approval_bound_and_exactly_scoped(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    clients = FakeProofClients()
    clients.active = True
    service = DataHubAssertionProofService(
        settings,
        clients,
        clients,
        workspace_root=tmp_path,
    )

    result = await service.reset(approval_sha256=DEFAULT_PROOF_PLAN.sha256)

    assert result["status"] == "reset"
    assert clients.active is False
    status_calls = [call for call in clients.calls if call[0] == "status"]
    assert status_calls == [
        (
            "status",
            {
                "entity_type": "assertion",
                "entity_urn": ASSERTION_URN,
                "removed": True,
            },
        )
    ]
