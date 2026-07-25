from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lineage_fuzzer.allocation import AllocationViolation, validate_dataset_urn
from lineage_fuzzer.config import Settings
from lineage_fuzzer.domain.models import ApprovalReceipt, CampaignManifest, TargetDescriptor


class SafetyViolation(RuntimeError):
    """Raised when a fault target fails any default-deny safety check."""


@dataclass(frozen=True)
class SafetyEvidence:
    target_urn: str
    resolved_database_path: Path
    manifest_sha256: str
    checks: tuple[str, ...]


class SafetyGate:
    """Deterministic gate required by both controllers and fault adapters."""

    def __init__(self, settings: Settings, *, workspace_root: Path | None = None) -> None:
        self._settings = settings
        self._workspace_root = (workspace_root or Path.cwd()).resolve()
        self._allowed_paths = frozenset(
            self._normalize_path(path) for path in settings.allowed_database_paths
        )

    def authorize(
        self,
        *,
        target: TargetDescriptor,
        manifest: CampaignManifest,
        approval: ApprovalReceipt,
    ) -> SafetyEvidence:
        if not self._settings.injection_enabled:
            raise SafetyViolation("fault injection is disabled")

        if approval.manifest_sha256 != manifest.sha256:
            raise SafetyViolation("approval is not bound to this campaign manifest")

        if target not in manifest.targets:
            raise SafetyViolation("target is not present in the approved campaign manifest")

        try:
            identity = validate_dataset_urn(target.urn, self._settings)
        except AllocationViolation as error:
            raise SafetyViolation(str(error)) from error
        expected_name = (
            f"{self._settings.datahub_urn_prefix}"
            f"{target.schema_name}.{target.table_name}"
        )
        if identity.name != expected_name:
            raise SafetyViolation("target URN identity does not match target descriptor")

        if target.platform.casefold() not in {
            platform.casefold() for platform in self._settings.allowed_platforms
        }:
            raise SafetyViolation(f"platform is not allowlisted: {target.platform}")

        if target.environment.casefold() not in {
            environment.casefold() for environment in self._settings.allowed_environments
        }:
            raise SafetyViolation(f"environment is not allowlisted: {target.environment}")

        resolved_path = self._normalize_path(target.database_path)
        if resolved_path not in self._allowed_paths:
            raise SafetyViolation(f"database path is not exactly allowlisted: {resolved_path}")

        marker = target.custom_properties.get(self._settings.required_marker_key)
        if marker is None or marker.casefold() != self._settings.required_marker_value.casefold():
            raise SafetyViolation("required DataHub sandbox marker is missing or invalid")

        if self._settings.datahub_project_tag not in target.tags:
            raise SafetyViolation("required DataHub project tag is missing")

        if self._settings.required_sandbox_tag not in target.tags:
            raise SafetyViolation("required DataHub sandbox tag is missing")

        return SafetyEvidence(
            target_urn=target.urn,
            resolved_database_path=resolved_path,
            manifest_sha256=manifest.sha256,
            checks=(
                "injection-explicitly-enabled",
                "approval-bound-to-manifest",
                "target-in-manifest",
                "urn-prefix-and-identity-allocated",
                "platform-allowlisted",
                "environment-allowlisted",
                "database-path-exactly-allowlisted",
                "datahub-sandbox-marker-present",
                "datahub-project-tag-present",
                "datahub-sandbox-tag-present",
            ),
        )

    def _normalize_path(self, path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self._workspace_root / candidate
        return candidate.resolve(strict=False)
