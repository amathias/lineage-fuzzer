from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lineage_fuzzer.domain.models import (
    ApprovalReceipt,
    CampaignManifest,
    DataHubContextSnapshot,
    FaultKind,
)
from lineage_fuzzer.pipeline.models import ControlResult


class MutationEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    fault_id: str
    kind: FaultKind
    mutated_primary_keys: tuple[int, ...]
    before_values_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    after_values_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BlastRadiusEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    predicted_urns: tuple[str, ...]
    observed_urns: tuple[str, ...]
    matched_urns: tuple[str, ...]
    missed_urns: tuple[str, ...]
    unexpected_urns: tuple[str, ...]

    @property
    def exact_match(self) -> bool:
        return not self.missed_urns and not self.unexpected_urns


class FaultRunEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    fault_id: str
    kind: FaultKind
    safety_checks: tuple[str, ...]
    mutation: MutationEvidence
    controls: tuple[ControlResult, ...]
    failing_control_ids: tuple[str, ...]
    detected: bool
    blast_radius: BlastRadiusEvidence
    artifact_violations: dict[str, int] = Field(default_factory=dict)
    restoration_verified: bool


class DetectionMatrixRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    fault_id: str
    kind: FaultKind
    detected: bool
    failing_control_ids: tuple[str, ...]


class CoverageReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    phase: Literal["baseline", "improved"]
    detected_faults: int = Field(ge=0)
    total_faults: int = Field(gt=0)
    coverage_percent: float = Field(ge=0, le=100)
    matrix: tuple[DetectionMatrixRow, ...]
    fault_runs: tuple[FaultRunEvidence, ...]


class GeneratedControlArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_ids: tuple[str, ...]
    policy_checks: tuple[str, ...]
    clean_violations: dict[str, int]
    clean_execution_passed: bool


class CampaignExecutionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["proved_and_restored"] = "proved_and_restored"
    context: DataHubContextSnapshot
    manifest: CampaignManifest
    approval: ApprovalReceipt
    baseline: CoverageReport
    generated_artifact: GeneratedControlArtifact
    improved: CoverageReport
    baseline_checksums: dict[str, str]
    final_checksums: dict[str, str]
    restoration_verified: bool
    replay_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def coverage_report(
    phase: Literal["baseline", "improved"],
    fault_runs: tuple[FaultRunEvidence, ...],
) -> CoverageReport:
    matrix = tuple(
        DetectionMatrixRow(
            fault_id=run.fault_id,
            kind=run.kind,
            detected=run.detected,
            failing_control_ids=run.failing_control_ids,
        )
        for run in fault_runs
    )
    detected = sum(row.detected for row in matrix)
    total = len(matrix)
    return CoverageReport(
        phase=phase,
        detected_faults=detected,
        total_faults=total,
        coverage_percent=round((detected / total) * 100, 1),
        matrix=matrix,
        fault_runs=fault_runs,
    )


def replay_sha256(
    *,
    manifest: CampaignManifest,
    baseline: CoverageReport,
    improved: CoverageReport,
    generated_artifact_sha256: str,
    final_checksums: dict[str, str],
) -> str:
    payload = {
        "manifest_sha256": manifest.sha256,
        "baseline": baseline.model_dump(mode="json"),
        "improved": improved.model_dump(mode="json"),
        "generated_artifact_sha256": generated_artifact_sha256,
        "final_checksums": dict(sorted(final_checksums.items())),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
