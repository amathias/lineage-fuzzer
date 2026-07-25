from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from lineage_fuzzer.config import Settings
from lineage_fuzzer.datahub.fixture_catalog import catalog_plan

ROOT = Path(__file__).resolve().parents[1]


def test_proven_datahub_clients_are_exactly_pinned() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"mcp==1.28.1"' in pyproject
    assert '"acryl-datahub==1.6.0.15"' in pyproject
    assert "mcp>=" not in pyproject
    assert "acryl-datahub>=" not in pyproject


def test_archive_verifier_covers_wheel_import_ui_fixture_and_checks() -> None:
    script = (ROOT / "scripts" / "verify_archive.ps1").read_text(encoding="utf-8")

    for required in (
        "git -C $repository archive",
        "-m pip wheel",
        "--force-reinstall --no-deps",
        "import datahub, lineage_fuzzer, mcp",
        "-m pytest -q",
        "-m ruff check src tests scripts",
        "lineage_fuzzer.pipeline_cli seed",
        "lineage_fuzzer.pipeline_cli controls",
        "TestClient(create_app())",
        "scripts/scan_secrets.py",
    ):
        assert required in script


def test_seed_aspects_deserialize_with_pinned_datahub_sdk() -> None:
    pytest.importorskip("datahub")
    from datahub.metadata.schema_classes import (
        DatasetPropertiesClass,
        DomainsClass,
        GlobalTagsClass,
        OwnershipClass,
        SchemaMetadataClass,
        StatusClass,
        UpstreamLineageClass,
    )

    aspect_classes = {
        "datasetProperties": DatasetPropertiesClass,
        "domains": DomainsClass,
        "globalTags": GlobalTagsClass,
        "ownership": OwnershipClass,
        "schemaMetadata": SchemaMetadataClass,
        "status": StatusClass,
        "upstreamLineage": UpstreamLineageClass,
    }
    operations = catalog_plan(Settings(_env_file=None))["aspects"]

    deserialized = [
        aspect_classes[operation["aspect_name"]].from_obj(operation["value"])
        for operation in operations
        if operation["aspect_name"] in aspect_classes
    ]

    assert len(deserialized) == 42


def test_tracked_repository_secret_scan_is_clean() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "scan_secrets.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "secret_scan=clean" in result.stdout
