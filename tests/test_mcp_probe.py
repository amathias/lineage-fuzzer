from lineage_fuzzer.datahub.mcp import DataHubMCPProbe


def test_probe_requires_context_tools() -> None:
    probe = DataHubMCPProbe(
        endpoint="http://localhost:8080/mcp",
        available_tools=("get_entities", "get_lineage"),
        required_tools=("get_entities", "get_lineage", "list_schema_fields"),
    )

    assert not probe.ready
    assert probe.missing_tools == ("list_schema_fields",)
