from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lineage_fuzzer.config import Settings

PROJECT_SLUG = "lineage-fuzzer"
DATAHUB_DOMAIN = "Demo / Lineage Fuzzer"
DATAHUB_PROJECT_TAG = "project-lineage-fuzzer"
DATAHUB_URN_PREFIX = "fuzzer."
SANDBOX_TAG = "lineage-fuzzer-sandbox"
FIXTURE_ROOT = Path("demo/fixtures/lineage-fuzzer")
FIXTURE_FILENAME = "lineage_fuzzer.duckdb"

_DATASET_URN = re.compile(
    r"^urn:li:dataset:\(urn:li:dataPlatform:(?P<platform>[^,]+),"
    r"(?P<name>[^,]+),(?P<environment>[^)]+)\)$"
)


class AllocationViolation(RuntimeError):
    """Raised when runtime state falls outside the frozen coordinator allocation."""


@dataclass(frozen=True)
class DatasetIdentity:
    urn: str
    platform: str
    name: str
    environment: str


def validate_allocation_settings(settings: Settings, *, workspace_root: Path) -> Path:
    checks = {
        "PROJECT_SLUG": (settings.project_slug, PROJECT_SLUG),
        "DATAHUB_DOMAIN": (settings.datahub_domain, DATAHUB_DOMAIN),
        "DATAHUB_PROJECT_TAG": (settings.datahub_project_tag, DATAHUB_PROJECT_TAG),
        "DATAHUB_URN_PREFIX": (settings.datahub_urn_prefix, DATAHUB_URN_PREFIX),
        "LINEAGE_FUZZER_REQUIRED_SANDBOX_TAG": (
            settings.required_sandbox_tag,
            SANDBOX_TAG,
        ),
    }
    mismatches = [
        name for name, (actual, expected) in checks.items() if actual != expected
    ]
    if mismatches:
        raise AllocationViolation(
            f"runtime allocation differs from coordinator contract: {', '.join(mismatches)}"
        )

    fixture_root = _resolve(settings.fixture_root, workspace_root)
    expected_root = _resolve(FIXTURE_ROOT, workspace_root)
    if fixture_root != expected_root:
        raise AllocationViolation("DEMO_FIXTURE_ROOT differs from coordinator allocation")

    expected_database = (fixture_root / FIXTURE_FILENAME).resolve(strict=False)
    allowed_paths = {
        _resolve(Path(path), workspace_root) for path in settings.allowed_database_paths
    }
    if allowed_paths != {expected_database}:
        raise AllocationViolation(
            "database allowlist must contain only the allocated fixture database"
        )

    validate_dataset_urn(settings.readiness_dataset_urn, settings)
    return expected_database


def validate_dataset_urn(urn: str, settings: Settings) -> DatasetIdentity:
    match = _DATASET_URN.fullmatch(urn)
    if not match:
        raise AllocationViolation("entity URN is not a valid DataHub dataset URN")
    identity = DatasetIdentity(urn=urn, **match.groupdict())
    if identity.platform.casefold() not in {
        platform.casefold() for platform in settings.allowed_platforms
    }:
        raise AllocationViolation("entity platform is outside the allowlist")
    if identity.environment.casefold() not in {
        environment.casefold() for environment in settings.allowed_environments
    }:
        raise AllocationViolation("entity environment is outside the allowlist")
    if not identity.name.startswith(settings.datahub_urn_prefix):
        raise AllocationViolation("entity name is outside the allocated URN prefix")
    return identity


def validate_assertion_urn(urn: str, settings: Settings) -> None:
    expected_prefix = f"urn:li:assertion:{settings.datahub_urn_prefix}"
    if not urn.startswith(expected_prefix):
        raise AllocationViolation("assertion URN is outside the allocated URN prefix")


def _resolve(path: Path, workspace_root: Path) -> Path:
    if not path.is_absolute():
        path = workspace_root / path
    return path.resolve(strict=False)
