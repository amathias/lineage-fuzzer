from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class TableChecksum(BaseModel):
    model_config = ConfigDict(frozen=True)

    table_name: str
    row_count: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FixtureEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    seed: int
    database_path: Path
    created_at: datetime
    tables: tuple[TableChecksum, ...]

    @property
    def checksum_map(self) -> dict[str, str]:
        return {table.table_name: table.sha256 for table in self.tables}


class FixtureSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    database_path: Path
    backup_path: Path
    seed: int
    created_at: datetime
    checksums: tuple[TableChecksum, ...]

    @property
    def checksum_map(self) -> dict[str, str]:
        return {table.table_name: table.sha256 for table in self.checksums}


class ControlDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    control_id: str
    description: str
    target_table: str
    violation_query: str
    detects_faults: tuple[str, ...] = ()


class ControlResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    control_id: str
    target_table: str
    passed: bool
    violation_count: int = Field(ge=0)
    detects_faults: tuple[str, ...] = ()
