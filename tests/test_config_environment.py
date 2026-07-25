from __future__ import annotations

import pytest

from lineage_fuzzer.config import Settings


def test_csv_list_environment_values_bypass_json_decoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS",
        "demo/one.duckdb, demo/two.duckdb",
    )
    monkeypatch.setenv("LINEAGE_FUZZER_ALLOWED_ENVIRONMENTS", "DEV, CI")
    monkeypatch.setenv("LINEAGE_FUZZER_ALLOWED_PLATFORMS", "duckdb, sqlite")

    settings = Settings(_env_file=None)

    assert settings.allowed_database_paths == [
        "demo/one.duckdb",
        "demo/two.duckdb",
    ]
    assert settings.allowed_environments == ["DEV", "CI"]
    assert settings.allowed_platforms == ["duckdb", "sqlite"]


def test_programmatic_list_values_remain_supported() -> None:
    settings = Settings(
        LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS=["demo/fixture.duckdb"],
        LINEAGE_FUZZER_ALLOWED_ENVIRONMENTS=["DEV"],
        LINEAGE_FUZZER_ALLOWED_PLATFORMS=["duckdb"],
    )

    assert settings.allowed_database_paths == ["demo/fixture.duckdb"]
