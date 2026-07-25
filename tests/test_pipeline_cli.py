from __future__ import annotations

import json
from pathlib import Path

from lineage_fuzzer.pipeline_cli import main


def cli_prefix(fixture_root: Path) -> list[str]:
    return [
        "--database",
        str(fixture_root / "lineage_fuzzer.duckdb"),
        "--fixture-root",
        str(fixture_root),
    ]


def test_seed_controls_snapshot_and_restore_commands(
    tmp_path: Path,
    capsys: object,
) -> None:
    fixture_root = tmp_path / "demo" / "fixtures" / "lineage-fuzzer"
    manifest_path = fixture_root / ".snapshots" / "demo.json"

    assert main([*cli_prefix(fixture_root), "seed", "--seed", "91"]) == 0
    seed_output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert seed_output["seed"] == 91

    assert main([*cli_prefix(fixture_root), "controls"]) == 0
    controls_output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert controls_output["status"] == "passed"

    assert (
        main(
            [
                *cli_prefix(fixture_root),
                "snapshot",
                "--manifest",
                str(manifest_path),
            ]
        )
        == 0
    )
    snapshot_output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert snapshot_output["manifest_path"] == str(manifest_path.resolve(strict=False))

    assert main([*cli_prefix(fixture_root), "restore", str(manifest_path)]) == 0
    restore_output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert restore_output["status"] == "restored"
