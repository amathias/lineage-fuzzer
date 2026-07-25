from __future__ import annotations

import inspect

from lineage_fuzzer.datahub.mcp import _McpSessionContext


def test_mcp_session_uses_installed_streamable_http_api() -> None:
    source = inspect.getsource(_McpSessionContext.__aenter__)

    assert "http_client=http_client" in source
    assert "headers=self._headers" in source
