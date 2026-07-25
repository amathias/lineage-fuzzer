from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


CsvList = Annotated[list[str], BeforeValidator(_split_csv)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field("development", alias="LINEAGE_FUZZER_ENVIRONMENT")
    state_dir: Path = Field(Path(".lineage-fuzzer"), alias="LINEAGE_FUZZER_STATE_DIR")

    injection_enabled: bool = Field(False, alias="LINEAGE_FUZZER_INJECTION_ENABLED")
    allowed_database_paths: CsvList = Field(
        default_factory=lambda: ["demo/data/lineage_fuzzer.duckdb"],
        alias="LINEAGE_FUZZER_ALLOWED_DATABASE_PATHS",
    )
    allowed_environments: CsvList = Field(
        default_factory=lambda: ["DEV"],
        alias="LINEAGE_FUZZER_ALLOWED_ENVIRONMENTS",
    )
    allowed_platforms: CsvList = Field(
        default_factory=lambda: ["duckdb"],
        alias="LINEAGE_FUZZER_ALLOWED_PLATFORMS",
    )
    required_sandbox_tag: str = Field(
        "lineage-fuzzer-sandbox",
        alias="LINEAGE_FUZZER_REQUIRED_SANDBOX_TAG",
    )
    required_marker_key: str = Field(
        "sandbox",
        alias="LINEAGE_FUZZER_REQUIRED_MARKER_KEY",
    )
    required_marker_value: str = Field(
        "true",
        alias="LINEAGE_FUZZER_REQUIRED_MARKER_VALUE",
    )

    datahub_gms_url: str = Field("http://localhost:8080", alias="DATAHUB_GMS_URL")
    datahub_mcp_url: str = Field("http://localhost:8080/mcp", alias="DATAHUB_MCP_URL")
    datahub_token: str | None = Field(None, alias="DATAHUB_TOKEN")
    datahub_mcp_timeout_seconds: float = Field(
        15,
        gt=0,
        alias="DATAHUB_MCP_TIMEOUT_SECONDS",
    )
