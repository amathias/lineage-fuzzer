from __future__ import annotations

import json
import socket

import pytest

from lineage_fuzzer.cli import main


def test_probe_reports_unavailable_datahub_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def refuse_connection(*args: object, **kwargs: object) -> socket.socket:
        raise ConnectionRefusedError

    monkeypatch.setattr(socket, "create_connection", refuse_connection)

    assert main(["probe-datahub"]) == 2
    captured = capsys.readouterr()
    assert '"ready": false' in captured.err
    assert "DataHub is not reachable" in captured.err


def test_show_datahub_plans_prints_manifest_approval_without_secret(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DATAHUB_TOKEN", "must-not-be-printed")

    assert main(["show-datahub-plans"]) == 0

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert len(payload["catalog_fixture"]["approval_sha256"]) == 64
    assert len(payload["assertion_proof"]["approval_sha256"]) == 64
    assert "must-not-be-printed" not in output


def test_guarded_catalog_command_fails_without_environment_token(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("DATAHUB_TOKEN", raising=False)

    result = main(
        [
            "seed-datahub-fixture",
            "--approval-sha256",
            "0" * 64,
        ]
    )

    assert result == 2
    assert "DATAHUB_TOKEN is required" in capsys.readouterr().err
