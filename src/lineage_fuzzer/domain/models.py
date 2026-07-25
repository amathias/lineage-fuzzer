from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class FaultKind(StrEnum):
    NUMERIC_SCALE = "numeric_scale"
    STALE_PARTITION = "stale_partition"
    NULL_DENSITY_SURGE = "null_density_surge"


class TargetDescriptor(BaseModel):
    """The physical and catalog identity that must pass the safety gate."""

    model_config = ConfigDict(frozen=True)

    urn: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    database_path: Path
    schema_name: str = Field(min_length=1)
    table_name: str = Field(min_length=1)
    tags: frozenset[str] = Field(default_factory=frozenset)
    custom_properties: dict[str, str] = Field(default_factory=dict)

    @field_validator("platform", "environment")
    @classmethod
    def normalize_identity(cls, value: str) -> str:
        return value.strip()

    @field_validator("database_path", mode="before")
    @classmethod
    def normalize_database_path(cls, value: object) -> object:
        return value.replace("\\", "/") if isinstance(value, str) else value

    @field_serializer("database_path")
    def serialize_database_path(self, value: Path) -> str:
        return value.as_posix()

    @field_serializer("tags")
    def serialize_tags(self, value: frozenset[str]) -> list[str]:
        return sorted(value)



class FaultSpecification(BaseModel):
    model_config = ConfigDict(frozen=True)

    fault_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    kind: FaultKind
    target_urn: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    expected_affected_urns: tuple[str, ...] = ()
    expected_control_urns: tuple[str, ...] = ()
    restore_action: str = Field(min_length=1)


class LineageEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    upstream_urn: str
    downstream_urn: str


class ContextProvenance(BaseModel):
    """Token-free binding between a live context and its exact runtime inputs."""

    model_config = ConfigDict(frozen=True)

    candidate_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    catalog_plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    catalog_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fixture_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tool_schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_response_sha256: dict[str, str]
    tool_schemas: tuple[dict[str, Any], ...]
    mcp_tools: tuple[str, ...]


class DataHubContextSnapshot(BaseModel):
    """Immutable DataHub evidence used to derive a campaign."""

    model_config = ConfigDict(frozen=True)

    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = "datahub-mcp"
    entities: tuple[dict[str, Any], ...] = ()
    lineage: tuple[LineageEdge, ...] = ()
    assertions: tuple[dict[str, Any], ...] = ()


    provenance: ContextProvenance | None = None
class CampaignManifest(BaseModel):
    """Replayable input to deterministic injection and scoring."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    campaign_id: UUID = Field(default_factory=uuid4)
    seed: int = Field(ge=0, le=2**63 - 1)
    graph_snapshot_sha256: str = Field(min_length=64, max_length=64)
    targets: tuple[TargetDescriptor, ...] = Field(min_length=1)
    faults: tuple[FaultSpecification, ...] = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_fault_targets(self) -> CampaignManifest:
        target_urns = {target.urn for target in self.targets}
        missing = {fault.target_urn for fault in self.faults} - target_urns
        if missing:
            raise ValueError(f"faults reference targets absent from manifest: {sorted(missing)}")
        fault_ids = [fault.fault_id for fault in self.faults]
        if len(fault_ids) != len(set(fault_ids)):
            raise ValueError("fault_id values must be unique within a campaign")
        return self

    def canonical_payload(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"created_at"})
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_payload()).hexdigest()


class ApprovalReceipt(BaseModel):
    """Explicit approval bound to one immutable manifest."""

    model_config = ConfigDict(frozen=True)

    manifest_sha256: str = Field(min_length=64, max_length=64)
    approved_by: str = Field(min_length=1)
    approved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def for_manifest(cls, manifest: CampaignManifest, *, approved_by: str) -> ApprovalReceipt:
        return cls(manifest_sha256=manifest.sha256, approved_by=approved_by)
