from __future__ import annotations

from pathlib import Path

import pytest

from lineage_fuzzer.config import Settings
from lineage_fuzzer.domain.models import ApprovalReceipt
from lineage_fuzzer.safety import SafetyGate, SafetyViolation
from tests.factories import make_approval, make_manifest, make_target


def enabled_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "LINEAGE_FUZZER_INJECTION_ENABLED": True,
        "LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS": [
            "demo/fixtures/lineage-fuzzer/lineage_fuzzer.duckdb"
        ],
        "LINEAGE_FUZZER_ALLOWED_ENVIRONMENTS": ["DEV"],
        "LINEAGE_FUZZER_ALLOWED_PLATFORMS": ["duckdb"],
    }
    values.update(overrides)
    return Settings(**values)


def test_allows_only_fully_marked_approved_fixture(tmp_path: Path) -> None:
    target = make_target()
    manifest = make_manifest(target)
    gate = SafetyGate(enabled_settings(), workspace_root=tmp_path)

    evidence = gate.authorize(
        target=target,
        manifest=manifest,
        approval=make_approval(manifest),
    )

    assert evidence.target_urn == target.urn
    assert (
        evidence.resolved_database_path
        == (
            tmp_path / "demo/fixtures/lineage-fuzzer/lineage_fuzzer.duckdb"
        ).resolve()
    )
    assert "datahub-sandbox-marker-present" in evidence.checks


def test_denies_when_injection_is_not_explicitly_enabled(tmp_path: Path) -> None:
    target = make_target()
    manifest = make_manifest(target)
    gate = SafetyGate(
        Settings(LINEAGE_FUZZER_INJECTION_ENABLED=False),
        workspace_root=tmp_path,
    )

    with pytest.raises(SafetyViolation, match="disabled"):
        gate.authorize(
            target=target,
            manifest=manifest,
            approval=make_approval(manifest),
        )


@pytest.mark.parametrize(
    ("target", "message"),
    [
        (
            make_target("../production.duckdb"),
            "database path is not exactly allowlisted",
        ),
        (
            make_target().model_copy(update={"environment": "PROD"}),
            "environment is not allowlisted",
        ),
        (
            make_target().model_copy(update={"platform": "postgres"}),
            "platform is not allowlisted",
        ),
        (
            make_target().model_copy(
                update={"tags": frozenset({"project-lineage-fuzzer"})}
            ),
            "sandbox tag is missing",
        ),
        (
            make_target().model_copy(
                update={"tags": frozenset({"lineage-fuzzer-sandbox"})}
            ),
            "project tag is missing",
        ),
        (
            make_target().model_copy(
                update={
                    "urn": "urn:li:dataset:(urn:li:dataPlatform:duckdb,other.raw.orders,DEV)"
                }
            ),
            "outside the allocated URN prefix",
        ),
        (
            make_target().model_copy(update={"custom_properties": {}}),
            "sandbox marker is missing",
        ),
    ],
)
def test_denies_target_that_fails_any_safety_dimension(
    tmp_path: Path,
    target: object,
    message: str,
) -> None:
    manifest = make_manifest(target)
    gate = SafetyGate(enabled_settings(), workspace_root=tmp_path)

    with pytest.raises(SafetyViolation, match=message):
        gate.authorize(
            target=target,
            manifest=manifest,
            approval=make_approval(manifest),
        )


def test_denies_approval_bound_to_different_manifest(tmp_path: Path) -> None:
    target = make_target()
    manifest = make_manifest(target)
    approval = ApprovalReceipt(
        manifest_sha256="f" * 64,
        approved_by="different-campaign",
    )
    gate = SafetyGate(enabled_settings(), workspace_root=tmp_path)

    with pytest.raises(SafetyViolation, match="not bound"):
        gate.authorize(target=target, manifest=manifest, approval=approval)
