from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from lineage_fuzzer.pipeline import DEFAULT_FIXTURE_PATH, DEFAULT_SEED, CommerceFixture
from lineage_fuzzer.pipeline.models import FixtureSnapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lineage_fuzzer.pipeline_cli",
        description="Manage the disposable Lineage Fuzzer DuckDB fixture.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help=f"fixture database path (default: {DEFAULT_FIXTURE_PATH})",
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=DEFAULT_FIXTURE_PATH.parent,
        help="exact project fixture boundary",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser(
        "seed", help="atomically build a clean deterministic fixture"
    )
    seed_parser.add_argument("--seed", type=int, default=DEFAULT_SEED)

    subparsers.add_parser("evidence", help="print canonical checksums for managed tables")
    subparsers.add_parser("controls", help="run baseline data-quality controls")

    snapshot_parser = subparsers.add_parser("snapshot", help="capture an exact restorable snapshot")
    snapshot_parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="snapshot manifest path (defaults beside the backup)",
    )

    restore_parser = subparsers.add_parser("restore", help="restore and verify a snapshot manifest")
    restore_parser.add_argument("manifest", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fixture = CommerceFixture(args.database, fixture_root=args.fixture_root)

    if args.command == "seed":
        evidence = fixture.seed(seed=args.seed)
        _print_json(evidence.model_dump(mode="json"))
        return 0

    if args.command == "evidence":
        _print_json(fixture.evidence().model_dump(mode="json"))
        return 0

    if args.command == "controls":
        results = fixture.run_controls()
        _print_json(
            {
                "status": "passed" if all(result.passed for result in results) else "failed",
                "controls": [result.model_dump(mode="json") for result in results],
            }
        )
        return 0 if all(result.passed for result in results) else 2

    if args.command == "snapshot":
        snapshot = fixture.snapshot()
        manifest_path = (
            args.manifest.resolve(strict=False)
            if args.manifest
            else snapshot.backup_path.with_suffix(".json")
        )
        _write_manifest(manifest_path, snapshot)
        _print_json(
            {
                "snapshot_id": snapshot.snapshot_id,
                "backup_path": str(snapshot.backup_path),
                "manifest_path": str(manifest_path),
            }
        )
        return 0

    if args.command == "restore":
        snapshot = FixtureSnapshot.model_validate_json(args.manifest.read_text(encoding="utf-8"))
        evidence = fixture.restore(snapshot)
        _print_json(
            {
                "status": "restored",
                "snapshot_id": snapshot.snapshot_id,
                "checksums": evidence.checksum_map,
            }
        )
        return 0

    raise AssertionError(f"unhandled command: {args.command}")


def _write_manifest(path: Path, snapshot: FixtureSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    temporary_path.replace(path)


def _print_json(value: object) -> None:
    json.dump(value, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
