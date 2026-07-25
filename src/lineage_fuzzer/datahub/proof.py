from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from lineage_fuzzer.allocation import (
    PROJECT_SLUG,
    AllocationViolation,
    validate_allocation_settings,
    validate_assertion_urn,
    validate_dataset_urn,
)
from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.fixture_catalog import (
    DATASET_URN,
    validate_observed_dataset,
)
from lineage_fuzzer.datahub.protocols import WritebackReceipt
from lineage_fuzzer.datahub.receipts import ReceiptStore, sha256_json

ASSERTION_URN = "urn:li:assertion:fuzzer.catalog-proof.orders-nonempty"
PROOF_TIMESTAMP_MILLIS = 1784937600000


class ProofApprovalViolation(RuntimeError):
    """Raised before network I/O when proof approval is absent or mismatched."""


class ProofVerificationError(RuntimeError):
    """Raised when the DataHub re-read does not prove the expected state."""


class AssertionGraphQL(Protocol):
    async def assertions_for_dataset(self, dataset_urn: str) -> dict[str, Any]: ...

    async def upsert_custom_assertion(
        self,
        *,
        assertion_urn: str,
        entity_urn: str,
        assertion_type: str,
        description: str,
        logic: str,
        field_path: str | None = None,
    ) -> WritebackReceipt: ...

    async def report_assertion_result(
        self,
        *,
        assertion_urn: str,
        result_type: str,
        properties: dict[str, str],
        timestamp_millis: int | None = None,
    ) -> WritebackReceipt: ...


class AssertionStatusWriter(Protocol):
    async def get_entity(
        self,
        *,
        entity_type: str,
        entity_urn: str,
        aspect_names: tuple[str, ...],
    ) -> Any: ...

    async def set_soft_deleted(
        self,
        *,
        entity_type: str,
        entity_urn: str,
        removed: bool,
    ) -> dict[str, Any]: ...


class DataHubProofPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_slug: str = PROJECT_SLUG
    dataset_urn: str = DATASET_URN
    assertion_urn: str = ASSERTION_URN
    assertion_type: str = "Lineage Fuzzer Live Proof"
    description: str = (
        "Disposable proof that Lineage Fuzzer can write and restore a custom assertion."
    )
    logic: str = "SELECT COUNT(*) > 0 FROM fuzzer.raw.orders"
    result_type: str = "SUCCESS"
    timestamp_millis: int = PROOF_TIMESTAMP_MILLIS
    properties: tuple[tuple[str, str], ...] = (
        ("project_slug", PROJECT_SLUG),
        ("proof", "catalog-writeback"),
        ("sandbox", "true"),
    )

    @property
    def sha256(self) -> str:
        return sha256_json(self.model_dump(mode="json"))


DEFAULT_PROOF_PLAN = DataHubProofPlan()


class DataHubAssertionProofService:
    """Executes one manifest-approved assertion proof and always restores it."""

    def __init__(
        self,
        settings: Settings,
        graphql: AssertionGraphQL,
        catalog: AssertionStatusWriter,
        *,
        workspace_root: Path,
        plan: DataHubProofPlan = DEFAULT_PROOF_PLAN,
    ) -> None:
        self.settings = settings
        self.graphql = graphql
        self.catalog = catalog
        self.workspace_root = workspace_root.resolve()
        self.plan = plan

    async def run(self, *, approval_sha256: str) -> dict[str, Any]:
        self._guard(approval_sha256)
        store = self._store()
        await self._verify_catalog_allocation()
        paths: dict[str, str] = {}

        before = _normalize_assertions(
            await self.graphql.assertions_for_dataset(self.plan.dataset_urn)
        )
        if _contains_assertion(before, self.plan.assertion_urn):
            raise ProofVerificationError(
                "proof assertion already exists; run the guarded reset command first"
            )
        paths["before"] = str(
            store.write(
                "before",
                plan_sha256=self.plan.sha256,
                payload={"dataset_urn": self.plan.dataset_urn, "assertions": before},
            )
        )

        write_recorded = False
        try:
            upsert = await self.graphql.upsert_custom_assertion(
                assertion_urn=self.plan.assertion_urn,
                entity_urn=self.plan.dataset_urn,
                assertion_type=self.plan.assertion_type,
                description=self.plan.description,
                logic=self.plan.logic,
            )
            if upsert.entity_urn != self.plan.assertion_urn:
                raise ProofVerificationError(
                    "DataHub returned a different assertion URN than the approved plan"
                )
            await self.catalog.set_soft_deleted(
                entity_type="assertion",
                entity_urn=self.plan.assertion_urn,
                removed=False,
            )
            result = await self.graphql.report_assertion_result(
                assertion_urn=self.plan.assertion_urn,
                result_type=self.plan.result_type,
                properties=dict(self.plan.properties),
                timestamp_millis=self.plan.timestamp_millis,
            )
            paths["write"] = str(
                store.write(
                    "write",
                    plan_sha256=self.plan.sha256,
                    payload={
                        "dataset_urn": self.plan.dataset_urn,
                        "assertion_urn": self.plan.assertion_urn,
                        "operations": [upsert.operation, "set_status_active", result.operation],
                        "result_type": self.plan.result_type,
                        "timestamp_millis": self.plan.timestamp_millis,
                    },
                )
            )
            write_recorded = True

            after = _normalize_assertions(
                await self.graphql.assertions_for_dataset(self.plan.dataset_urn)
            )
            _validate_after(after, self.plan)
            paths["after"] = str(
                store.write(
                    "after",
                    plan_sha256=self.plan.sha256,
                    payload={"dataset_urn": self.plan.dataset_urn, "assertions": after},
                )
            )
        except Exception as error:
            if not write_recorded:
                paths["write"] = str(
                    store.write(
                        "write",
                        plan_sha256=self.plan.sha256,
                        payload={
                            "dataset_urn": self.plan.dataset_urn,
                            "assertion_urn": self.plan.assertion_urn,
                            "status": "failed_closed",
                            "error_type": type(error).__name__,
                        },
                    )
                )
            raise
        finally:
            await self.catalog.set_soft_deleted(
                entity_type="assertion",
                entity_urn=self.plan.assertion_urn,
                removed=True,
            )
            restored = _normalize_assertions(
                await self.graphql.assertions_for_dataset(self.plan.dataset_urn)
            )
            if _contains_assertion(restored, self.plan.assertion_urn):
                raise ProofVerificationError(
                    "proof assertion remained attached after deterministic restore"
                )
            paths["restore"] = str(
                store.write(
                    "restore",
                    plan_sha256=self.plan.sha256,
                    payload={
                        "dataset_urn": self.plan.dataset_urn,
                        "assertion_urn": self.plan.assertion_urn,
                        "status": "soft_deleted_and_absent_from_dataset",
                        "assertions": restored,
                    },
                )
            )

        return {
            "status": "proved_and_restored",
            "plan_sha256": self.plan.sha256,
            "dataset_urn": self.plan.dataset_urn,
            "assertion_urn": self.plan.assertion_urn,
            "receipt_paths": paths,
        }

    async def reset(self, *, approval_sha256: str) -> dict[str, Any]:
        self._guard(approval_sha256)
        await self._verify_catalog_allocation()
        await self.catalog.set_soft_deleted(
            entity_type="assertion",
            entity_urn=self.plan.assertion_urn,
            removed=True,
        )
        restored = _normalize_assertions(
            await self.graphql.assertions_for_dataset(self.plan.dataset_urn)
        )
        if _contains_assertion(restored, self.plan.assertion_urn):
            raise ProofVerificationError("proof assertion remained attached after reset")
        path = self._store().write(
            "restore",
            plan_sha256=self.plan.sha256,
            payload={
                "dataset_urn": self.plan.dataset_urn,
                "assertion_urn": self.plan.assertion_urn,
                "status": "soft_deleted_and_absent_from_dataset",
                "assertions": restored,
            },
        )
        return {
            "status": "reset",
            "plan_sha256": self.plan.sha256,
            "receipt_path": str(path),
        }

    def _guard(self, approval_sha256: str) -> None:
        if approval_sha256 != self.plan.sha256:
            raise ProofApprovalViolation(
                "approval SHA-256 does not match the immutable DataHub proof plan"
            )
        validate_allocation_settings(self.settings, workspace_root=self.workspace_root)
        validate_dataset_urn(self.plan.dataset_urn, self.settings)
        validate_assertion_urn(self.plan.assertion_urn, self.settings)
        if self.plan != DEFAULT_PROOF_PLAN:
            raise AllocationViolation("proof plan differs from the fixed coordinator plan")
        if self.plan.dataset_urn != self.settings.readiness_dataset_urn:
            raise AllocationViolation("proof dataset is not the exact readiness allocation")
        if dict(self.plan.properties).get("sandbox", "").casefold() != "true":
            raise AllocationViolation("proof plan is missing sandbox=true")

    async def _verify_catalog_allocation(self) -> None:
        observed = await self.catalog.get_entity(
            entity_type="dataset",
            entity_urn=self.plan.dataset_urn,
            aspect_names=("datasetProperties", "globalTags", "domains", "status"),
        )
        validate_observed_dataset(observed, self.settings, self.plan.dataset_urn)

    def _store(self) -> ReceiptStore:
        return ReceiptStore(
            self.settings.state_dir,
            workspace_root=self.workspace_root,
            run_id=f"assertion-{self.plan.sha256[:16]}",
        )


def _normalize_assertions(response: dict[str, Any]) -> list[dict[str, Any]]:
    dataset = response.get("dataset")
    if not isinstance(dataset, dict):
        return []
    connection = dataset.get("assertions")
    if not isinstance(connection, dict):
        return []
    assertions = connection.get("assertions")
    if not isinstance(assertions, list):
        return []

    normalized: list[dict[str, Any]] = []
    for assertion in assertions:
        if not isinstance(assertion, dict) or not isinstance(assertion.get("urn"), str):
            continue
        info = assertion.get("info") if isinstance(assertion.get("info"), dict) else {}
        custom = (
            info.get("customAssertion")
            if isinstance(info.get("customAssertion"), dict)
            else {}
        )
        run_events = (
            assertion.get("runEvents")
            if isinstance(assertion.get("runEvents"), dict)
            else {}
        )
        events = run_events.get("runEvents")
        latest = events[0] if isinstance(events, list) and events else {}
        result = latest.get("result") if isinstance(latest, dict) else {}
        native = result.get("nativeResults") if isinstance(result, dict) else []
        properties = {
            item["key"]: item["value"]
            for item in native
            if isinstance(item, dict)
            and isinstance(item.get("key"), str)
            and isinstance(item.get("value"), str)
        } if isinstance(native, list) else {}
        normalized.append(
            {
                "urn": assertion["urn"],
                "entity_urn": custom.get("entityUrn"),
                "custom_type": info.get("customType"),
                "result_type": result.get("type") if isinstance(result, dict) else None,
                "result_properties": dict(sorted(properties.items())),
                "timestamp_millis": latest.get("timestampMillis")
                if isinstance(latest, dict)
                else None,
            }
        )
    return sorted(normalized, key=lambda item: item["urn"])


def _contains_assertion(assertions: list[dict[str, Any]], assertion_urn: str) -> bool:
    return any(assertion.get("urn") == assertion_urn for assertion in assertions)


def _validate_after(assertions: list[dict[str, Any]], plan: DataHubProofPlan) -> None:
    match = next(
        (assertion for assertion in assertions if assertion.get("urn") == plan.assertion_urn),
        None,
    )
    if match is None:
        raise ProofVerificationError("proof assertion was absent from the DataHub re-read")
    if match.get("entity_urn") != plan.dataset_urn:
        raise ProofVerificationError("proof assertion re-read returned a foreign entity")
    if match.get("result_type") != plan.result_type:
        raise ProofVerificationError("proof assertion result was not visible on re-read")
    if match.get("timestamp_millis") != plan.timestamp_millis:
        raise ProofVerificationError("proof assertion timestamp differed from the approved plan")
    if match.get("result_properties") != dict(plan.properties):
        raise ProofVerificationError("proof assertion properties differed from the approved plan")
