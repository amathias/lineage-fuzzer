from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from lineage_fuzzer.allocation import validate_allocation_settings
from lineage_fuzzer.campaign.context import (
    TABLE_URNS,
    baseline_controls_from_context,
    context_sha256,
)
from lineage_fuzzer.campaign.generation import (
    GENERATED_CONTROLS,
    GeneratedControlService,
)
from lineage_fuzzer.campaign.models import (
    BlastRadiusEvidence,
    CampaignExecutionReport,
    FaultRunEvidence,
    coverage_report,
    replay_sha256,
)
from lineage_fuzzer.campaign.planner import build_campaign_manifest
from lineage_fuzzer.config import Settings
from lineage_fuzzer.domain.models import (
    ApprovalReceipt,
    CampaignManifest,
    DataHubContextSnapshot,
    FaultSpecification,
    TargetDescriptor,
)
from lineage_fuzzer.pipeline import CommerceFixture, FixtureSnapshot
from lineage_fuzzer.pipeline.faults import default_fault_adapters
from lineage_fuzzer.pipeline.models import ControlDefinition
from lineage_fuzzer.safety import SafetyGate, SafetyViolation


class CampaignExecutionError(RuntimeError):
    """Raised when deterministic campaign evidence does not satisfy its contract."""


class CampaignRunner:
    """Execute the fixed campaign with verified restoration between every fault."""

    def __init__(
        self,
        settings: Settings,
        context: DataHubContextSnapshot,
        *,
        workspace_root: Path,
        artifact_root: Path,
        evidence_root: Path,
    ) -> None:
        self.settings = settings
        self.context = context
        self.workspace_root = workspace_root.resolve()
        self.database_path = validate_allocation_settings(
            settings,
            workspace_root=self.workspace_root,
        )
        self.fixture_root = _resolve(settings.fixture_root, self.workspace_root)
        self.artifact_service = GeneratedControlService(artifact_root)
        self.evidence_root = evidence_root.resolve(strict=False)
        self.safety_gate = SafetyGate(settings, workspace_root=self.workspace_root)
        self.baseline_controls = baseline_controls_from_context(context)
        self.adapters = default_fault_adapters(self.safety_gate)

    def plan(self) -> CampaignManifest:
        return build_campaign_manifest(
            self.context,
            database_path=self.settings.allowed_database_paths[0],
        )

    def run(
        self,
        *,
        approval_sha256: str,
        approved_by: str = "judge-demo",
    ) -> CampaignExecutionReport:
        manifest = self.plan()
        approval = ApprovalReceipt(
            approved_at=manifest.created_at,
            manifest_sha256=approval_sha256,
            approved_by=approved_by,
        )
        target = manifest.targets[0]
        controller_safety = self.safety_gate.authorize(
            target=target,
            manifest=manifest,
            approval=approval,
        )
        fixture = CommerceFixture(
            self.database_path,
            fixture_root=self.fixture_root,
        )
        fixture.seed(seed=manifest.seed)
        baseline_evidence = fixture.evidence(seed=manifest.seed)
        snapshot = fixture.snapshot()

        report: CampaignExecutionReport | None = None
        try:
            baseline_runs = self._run_phase(
                fixture=fixture,
                snapshot=snapshot,
                manifest=manifest,
                approval=approval,
                target=target,
                controls=self.baseline_controls,
                safety_checks=controller_safety.checks,
                execute_artifact=False,
            )
            baseline = coverage_report("baseline", baseline_runs)
            if baseline.detected_faults != 1:
                raise CampaignExecutionError(
                    "baseline campaign did not produce the designed one-of-three coverage"
                )

            fixture.restore(snapshot)
            generated_artifact = self.artifact_service.generate_and_validate(fixture)
            improved_runs = self._run_phase(
                fixture=fixture,
                snapshot=snapshot,
                manifest=manifest,
                approval=approval,
                target=target,
                controls=self.baseline_controls + GENERATED_CONTROLS,
                safety_checks=controller_safety.checks,
                execute_artifact=True,
            )
            improved = coverage_report("improved", improved_runs)
            if improved.detected_faults != improved.total_faults:
                raise CampaignExecutionError(
                    "generated controls did not close every measured campaign gap"
                )
        finally:
            final_evidence = fixture.restore(snapshot)

        restoration_verified = final_evidence.checksum_map == baseline_evidence.checksum_map
        if not restoration_verified:
            raise CampaignExecutionError("final fixture checksums differ from campaign baseline")
        report = CampaignExecutionReport(
            context=self.context,
            manifest=manifest,
            approval=approval,
            baseline=baseline,
            generated_artifact=generated_artifact,
            improved=improved,
            baseline_checksums=baseline_evidence.checksum_map,
            final_checksums=final_evidence.checksum_map,
            restoration_verified=True,
            replay_sha256=replay_sha256(
                manifest=manifest,
                baseline=baseline,
                improved=improved,
                generated_artifact_sha256=generated_artifact.sha256,
                final_checksums=final_evidence.checksum_map,
            ),
        )
        self._write_evidence(report)
        return report

    def _run_phase(
        self,
        *,
        fixture: CommerceFixture,
        snapshot: FixtureSnapshot,
        manifest: CampaignManifest,
        approval: ApprovalReceipt,
        target: TargetDescriptor,
        controls: tuple[ControlDefinition, ...],
        safety_checks: tuple[str, ...],
        execute_artifact: bool,
    ) -> tuple[FaultRunEvidence, ...]:
        runs: list[FaultRunEvidence] = []
        for specification in manifest.faults:
            fixture.restore(snapshot)
            before = fixture.evidence(seed=manifest.seed)
            run: FaultRunEvidence | None = None
            try:
                self.safety_gate.authorize(
                    target=target,
                    manifest=manifest,
                    approval=approval,
                )
                adapter = self.adapters[specification.kind]
                mutation = adapter.apply(
                    fixture=fixture,
                    target=target,
                    specification=specification,
                    manifest=manifest,
                    approval=approval,
                )
                faulty = fixture.evidence(seed=manifest.seed)
                control_results = fixture.run_controls(controls)
                failing_control_ids = tuple(
                    sorted(
                        result.control_id
                        for result in control_results
                        if not result.passed
                    )
                )
                artifact_violations = (
                    self.artifact_service.execute(
                        self.artifact_service.artifact_path,
                        fixture,
                    )
                    if execute_artifact
                    else {}
                )
                blast_radius = _blast_radius(
                    specification,
                    before.checksum_map,
                    faulty.checksum_map,
                )
                if not blast_radius.exact_match:
                    raise CampaignExecutionError(
                        f"observed blast radius differed for {specification.fault_id}"
                    )
                run = FaultRunEvidence(
                    fault_id=specification.fault_id,
                    kind=specification.kind,
                    safety_checks=safety_checks,
                    mutation=mutation,
                    controls=control_results,
                    failing_control_ids=failing_control_ids,
                    detected=bool(failing_control_ids),
                    blast_radius=blast_radius,
                    artifact_violations=artifact_violations,
                    restoration_verified=True,
                )
            finally:
                restored = fixture.restore(snapshot)
            if restored.checksum_map != snapshot.checksum_map:
                raise CampaignExecutionError(
                    f"fixture restoration failed after {specification.fault_id}"
                )
            if run is None:
                raise CampaignExecutionError(
                    f"fault execution did not produce evidence: {specification.fault_id}"
                )
            runs.append(run)
        return tuple(runs)

    def _write_evidence(self, report: CampaignExecutionReport) -> None:
        manifest_digest = report.manifest.sha256
        context_digest = context_sha256(report.context)
        run_root = (
            self.evidence_root / f"m-{manifest_digest[:16]}-c-{context_digest[:16]}"
        ).resolve(strict=False)
        run_root.mkdir(parents=True, exist_ok=True)
        payloads: dict[str, Any] = {
            "campaign-manifest.json": report.manifest.model_dump(mode="json"),
            "baseline-coverage.json": report.baseline.model_dump(mode="json"),
            "final-coverage.json": report.improved.model_dump(mode="json"),
            "campaign-report.json": report.model_dump(mode="json"),
        }
        for name, payload in payloads.items():
            path = (run_root / name).resolve(strict=False)
            if run_root not in path.parents:
                raise CampaignExecutionError("campaign evidence path escaped its output root")
            _immutable_json(path, payload)
        artifact_source = self.artifact_service.artifact_path.resolve(strict=True)
        if artifact_source.name != report.generated_artifact.path.name:
            raise CampaignExecutionError("generated artifact report path is contradictory")
        if _sha256_file(artifact_source) != report.generated_artifact.sha256:
            raise CampaignExecutionError(
                "generated artifact bytes differ from their reported SHA-256"
            )
        artifact_destination = (
            run_root / "generated" / artifact_source.name
        ).resolve(strict=False)
        if run_root not in artifact_destination.parents:
            raise CampaignExecutionError("generated artifact evidence escaped its output root")
        artifact_destination.parent.mkdir(parents=True, exist_ok=True)
        _immutable_bytes(artifact_destination, artifact_source.read_bytes())



def _blast_radius(
    specification: FaultSpecification,
    before: dict[str, str],
    faulty: dict[str, str],
) -> BlastRadiusEvidence:
    observed = {
        TABLE_URNS[table]
        for table, checksum in before.items()
        if faulty.get(table) != checksum
    }
    predicted = set(specification.expected_affected_urns)
    return BlastRadiusEvidence(
        predicted_urns=tuple(sorted(predicted)),
        observed_urns=tuple(sorted(observed)),
        matched_urns=tuple(sorted(predicted & observed)),
        missed_urns=tuple(sorted(predicted - observed)),
        unexpected_urns=tuple(sorted(observed - predicted)),
    )


def require_plan_approval(manifest: CampaignManifest, approval_sha256: str) -> None:
    if approval_sha256 != manifest.sha256:
        raise SafetyViolation("approval is not bound to this campaign manifest")


def _immutable_json(path: Path, value: Any) -> None:
    serialized = f"{json.dumps(value, indent=2, sort_keys=True)}\n"
    if path.is_file():
        if path.read_text(encoding="utf-8") != serialized:
            raise CampaignExecutionError(
                "campaign replay would overwrite non-identical immutable evidence"
            )
        return
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(serialized, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _immutable_bytes(path: Path, value: bytes) -> None:
    if path.is_file():
        if path.read_bytes() != value:
            raise CampaignExecutionError(
                "campaign replay would overwrite non-identical immutable artifact"
            )
        return
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)

def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _resolve(path: Path, workspace_root: Path) -> Path:
    if not path.is_absolute():
        path = workspace_root / path
    return path.resolve(strict=False)
