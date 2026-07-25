from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ReceiptPathViolation(RuntimeError):
    """Raised when durable evidence would escape the configured state root."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class ReceiptStore:
    """Persists whitelisted, token-free proof records under the app state root."""

    def __init__(
        self,
        state_dir: Path,
        *,
        workspace_root: Path,
        run_id: str,
    ) -> None:
        root = state_dir if state_dir.is_absolute() else workspace_root / state_dir
        self._state_root = root.resolve(strict=False)
        if not self._state_root.is_dir():
            raise ReceiptPathViolation("configured state directory does not exist")
        self._run_dir = (
            self._state_root / "datahub-receipts" / run_id
        ).resolve(strict=False)
        if not self._run_dir.is_relative_to(self._state_root):
            raise ReceiptPathViolation("receipt path escapes the configured state directory")

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    def write(
        self,
        phase: str,
        *,
        plan_sha256: str,
        payload: dict[str, Any],
    ) -> Path:
        if phase not in {"before", "write", "after", "restore", "catalog"}:
            raise ReceiptPathViolation("receipt phase is not allowlisted")
        self._run_dir.mkdir(parents=True, exist_ok=True)
        envelope = {
            "schema_version": 1,
            "project_slug": "lineage-fuzzer",
            "phase": phase,
            "plan_sha256": plan_sha256,
            "recorded_at": datetime.now(UTC).isoformat(),
            "payload": payload,
            "payload_sha256": sha256_json(payload),
        }
        destination = self._run_dir / f"{phase}.json"
        temporary = self._run_dir / f".{phase}.json.tmp"
        temporary.write_text(
            json.dumps(envelope, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, destination)
        return destination
