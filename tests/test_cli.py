from __future__ import annotations

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
