from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, BeforeValidator, Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


CsvList = Annotated[list[str], NoDecode, BeforeValidator(_split_csv)]


class Settings(BaseSettings):
    """Application settings including the frozen portfolio allocation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_slug: str = Field("lineage-fuzzer", alias="PROJECT_SLUG")
    environment: str = Field(
        "development",
        validation_alias=AliasChoices("APP_ENV", "LINEAGE_FUZZER_ENVIRONMENT"),
    )
    state_dir: Path = Field(
        Path(".lineage-fuzzer"),
        validation_alias=AliasChoices("APP_STATE_DIR", "LINEAGE_FUZZER_STATE_DIR"),
    )
    campaign_context_file: Path | None = Field(
        None,
        alias="LINEAGE_FUZZER_CONTEXT_FILE",
    )
    candidate_sha: str | None = Field(
        None,
        pattern=r"^[0-9a-f]{40}$",
        alias="LINEAGE_FUZZER_CANDIDATE_SHA",
    )
    fixture_root: Path = Field(
        Path("demo/fixtures/lineage-fuzzer"),
        alias="DEMO_FIXTURE_ROOT",
    )

    injection_enabled: bool = Field(False, alias="LINEAGE_FUZZER_INJECTION_ENABLED")
    allowed_database_paths: CsvList = Field(
        default_factory=lambda: [
            "demo/fixtures/lineage-fuzzer/lineage_fuzzer.duckdb",
        ],
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
    datahub_mcp_url: str = Field("http://localhost:8000/mcp", alias="DATAHUB_MCP_URL")
    datahub_token: str | None = Field(None, alias="DATAHUB_TOKEN")
    datahub_domain: str = Field("Demo / Lineage Fuzzer", alias="DATAHUB_DOMAIN")
    datahub_project_tag: str = Field(
        "project-lineage-fuzzer",
        alias="DATAHUB_PROJECT_TAG",
    )
    datahub_urn_prefix: str = Field("fuzzer.", alias="DATAHUB_URN_PREFIX")
    readiness_dataset_urn: str = Field(
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,fuzzer.raw.orders,DEV)",
        alias="LINEAGE_FUZZER_READINESS_DATASET_URN",
    )
    datahub_mcp_timeout_seconds: float = Field(
        15,
        gt=0,
        alias="DATAHUB_MCP_TIMEOUT_SECONDS",
    )

    @property
    def is_hackathon(self) -> bool:
        return self.environment.casefold() == "hackathon"


__all__ = ["Settings"]
