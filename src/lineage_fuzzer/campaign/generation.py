from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb

from lineage_fuzzer.campaign.context import RAW_ORDERS_URN, context_sha256
from lineage_fuzzer.campaign.models import GeneratedControlArtifact
from lineage_fuzzer.domain.models import CampaignManifest, DataHubContextSnapshot, FaultKind
from lineage_fuzzer.pipeline.fixture import CommerceFixture
from lineage_fuzzer.pipeline.models import ControlDefinition

ARTIFACT_FILENAME = "lineage_fuzzer_generated_controls.sql"

_BANNED_SQL = re.compile(
    r"\b("
    r"ALTER|ATTACH|CALL|COPY|CREATE|DELETE|DETACH|DROP|EXECUTE|EXPORT|"
    r"IMPORT|INSERT|INSTALL|LOAD|MERGE|PRAGMA|SET|TRUNCATE|UPDATE|VACUUM"
    r")\b",
    re.IGNORECASE,
)

_NUMERIC_TYPES = frozenset({"BIGINT", "DECIMAL", "DOUBLE", "FLOAT", "HUGEINT", "INTEGER"})


class GeneratedSQLViolation(RuntimeError):
    """Raised when generated SQL or its metadata inputs violate the bounded contract."""


@dataclass(frozen=True)
class GeneratedControlSpec:
    control_id: str
    description: str
    target_table: str
    column: str
    operator: str
    sql_literal: str
    detects_fault: FaultKind

    def control_definition(self) -> ControlDefinition:
        return ControlDefinition(
            control_id=self.control_id,
            description=self.description,
            target_table=self.target_table,
            violation_query=(
                f"SELECT count(*) FROM {self.target_table} "
                f"WHERE {self.column} {self.operator} {self.sql_literal}"
            ),
            detects_faults=(self.detects_fault.value,),
        )


@dataclass(frozen=True)
class GeneratedControlBundle:
    artifact: GeneratedControlArtifact
    controls: tuple[ControlDefinition, ...]


class GeneratedControlService:
    """Generate, validate, and execute metadata-grounded read-only SQL controls."""

    def __init__(self, artifact_root: Path) -> None:
        self.artifact_root = artifact_root.resolve(strict=False)

    @property
    def artifact_path(self) -> Path:
        return (self.artifact_root / ARTIFACT_FILENAME).resolve(strict=False)

    def generate_and_validate(
        self,
        fixture: CommerceFixture,
        *,
        context: DataHubContextSnapshot,
        manifest: CampaignManifest,
        gap_faults: tuple[FaultKind, ...],
    ) -> GeneratedControlBundle:
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        path = self.artifact_path
        if self.artifact_root not in path.parents:
            raise GeneratedSQLViolation("generated artifact path escaped its output root")

        specs, profile = build_control_specs(
            fixture,
            context=context,
            manifest=manifest,
            gap_faults=gap_faults,
        )
        context_digest = context_sha256(context)
        profile_digest = _sha256_json(profile)
        sql = render_generated_control_sql(
            specs,
            context_sha256_value=context_digest,
            manifest_sha256=manifest.sha256,
            profile_sha256=profile_digest,
        )
        policy_checks = validate_generated_sql(sql)
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(sql, encoding="utf-8", newline="\n")
        temporary.replace(path)

        controls = tuple(spec.control_definition() for spec in specs)
        clean_violations = self.execute(path, fixture, controls=controls)
        if not all(value == 0 for value in clean_violations.values()):
            raise GeneratedSQLViolation("generated controls failed against the clean fixture")
        artifact = GeneratedControlArtifact(
            path=Path(ARTIFACT_FILENAME),
            sha256=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
            control_ids=tuple(control.control_id for control in controls),
            policy_checks=policy_checks,
            clean_violations=clean_violations,
            clean_execution_passed=True,
            source_context_sha256=context_digest,
            source_manifest_sha256=manifest.sha256,
            source_profile_sha256=profile_digest,
            generated_from_faults=gap_faults,
        )
        return GeneratedControlBundle(artifact=artifact, controls=controls)

    def execute(
        self,
        path: Path,
        fixture: CommerceFixture,
        *,
        controls: tuple[ControlDefinition, ...],
    ) -> dict[str, int]:
        resolved = path.resolve(strict=True)
        if self.artifact_root not in resolved.parents:
            raise GeneratedSQLViolation("generated artifact execution escaped its output root")
        sql = resolved.read_text(encoding="utf-8")
        validate_generated_sql(sql)
        with duckdb.connect(str(fixture.database_path), read_only=True) as connection:
            rows = connection.execute(sql).fetchall()
        result = {str(row[0]): int(row[1]) for row in rows}
        expected = {control.control_id for control in controls}
        if set(result) != expected:
            raise GeneratedSQLViolation("generated artifact returned unexpected control IDs")
        if any(value < 0 for value in result.values()):
            raise GeneratedSQLViolation("generated artifact returned a negative violation count")
        return dict(sorted(result.items()))


def build_control_specs(
    fixture: CommerceFixture,
    *,
    context: DataHubContextSnapshot,
    manifest: CampaignManifest,
    gap_faults: tuple[FaultKind, ...],
) -> tuple[tuple[GeneratedControlSpec, ...], dict[str, object]]:
    """Compile measured gaps into typed controls using DataHub schema and clean profiles."""

    if not gap_faults or len(gap_faults) != len(set(gap_faults)):
        raise GeneratedSQLViolation("measured campaign gaps are empty or duplicated")
    entity = next((item for item in context.entities if item.get("urn") == RAW_ORDERS_URN), None)
    if entity is None:
        raise GeneratedSQLViolation("DataHub context omits the campaign target")
    field_types = entity.get("schemaFieldTypes")
    if not isinstance(field_types, dict) or not all(
        isinstance(name, str) and isinstance(native_type, str)
        for name, native_type in field_types.items()
    ):
        raise GeneratedSQLViolation("DataHub context omits typed schema metadata")

    faults = {fault.kind: fault for fault in manifest.faults}
    unexpected = set(gap_faults) - {FaultKind.NUMERIC_SCALE, FaultKind.STALE_PARTITION}
    if unexpected:
        raise GeneratedSQLViolation(f"no bounded generator exists for gaps: {sorted(unexpected)}")

    profile: dict[str, object] = {
        "context_sha256": context_sha256(context),
        "manifest_sha256": manifest.sha256,
        "target_urn": RAW_ORDERS_URN,
        "gaps": [fault.value for fault in gap_faults],
    }
    specs: list[GeneratedControlSpec] = []
    with duckdb.connect(str(fixture.database_path), read_only=True) as connection:
        for gap in gap_faults:
            specification = faults.get(gap)
            if specification is None:
                raise GeneratedSQLViolation(f"manifest omits measured gap {gap.value}")
            if gap is FaultKind.NUMERIC_SCALE:
                column = _required_column(specification.parameters, "column")
                if str(field_types.get(column, "")).upper() not in _NUMERIC_TYPES:
                    raise GeneratedSQLViolation(
                        f"DataHub schema does not type {column} as numeric"
                    )
                maximum = connection.execute(
                    f"SELECT max({_quoted_identifier(column)}) FROM raw.orders"
                ).fetchone()[0]
                if isinstance(maximum, bool) or not isinstance(maximum, int):
                    raise GeneratedSQLViolation("clean numeric profile is not an integer")
                profile[gap.value] = {"column": column, "clean_max": maximum}
                specs.append(
                    GeneratedControlSpec(
                        control_id=f"orders_{column}_reasonable",
                        description=(
                            f"{column} must not exceed the clean campaign profile maximum."
                        ),
                        target_table="raw.orders",
                        column=_quoted_identifier(column),
                        operator=">",
                        sql_literal=str(maximum),
                        detects_fault=gap,
                    )
                )
            elif gap is FaultKind.STALE_PARTITION:
                column = _required_column(specification.parameters, "partition_column")
                if str(field_types.get(column, "")).upper() != "DATE":
                    raise GeneratedSQLViolation(
                        f"DataHub schema does not type {column} as DATE"
                    )
                minimum = connection.execute(
                    f"SELECT min({_quoted_identifier(column)}) FROM raw.orders"
                ).fetchone()[0]
                if not isinstance(minimum, date):
                    raise GeneratedSQLViolation("clean partition profile is not a date")
                profile[gap.value] = {
                    "column": column,
                    "clean_min": minimum.isoformat(),
                }
                specs.append(
                    GeneratedControlSpec(
                        control_id="orders_partition_not_stale",
                        description=(
                            f"{column} must not predate the clean campaign profile window."
                        ),
                        target_table="raw.orders",
                        column=_quoted_identifier(column),
                        operator="<",
                        sql_literal=f"DATE '{minimum.isoformat()}'",
                        detects_fault=gap,
                    )
                )
    return tuple(specs), profile


def render_generated_control_sql(
    specs: tuple[GeneratedControlSpec, ...],
    *,
    context_sha256_value: str,
    manifest_sha256: str,
    profile_sha256: str,
) -> str:
    if not specs:
        raise GeneratedSQLViolation("no control specifications were generated")
    statements = [
        "\n".join(
            (
                "SELECT",
                f"    '{spec.control_id}' AS control_id,",
                "    count(*)::BIGINT AS violation_count",
                f"FROM {spec.target_table}",
                f"WHERE {spec.column} {spec.operator} {spec.sql_literal}",
            )
        )
        for spec in specs
    ]
    return (
        "-- Generated from captured DataHub schema, measured gaps, and clean profile.\n"
        f"-- context_sha256={context_sha256_value}\n"
        f"-- manifest_sha256={manifest_sha256}\n"
        f"-- profile_sha256={profile_sha256}\n"
        "-- Read-only DuckDB test artifact; zero violations means the control passes.\n"
        + "\nUNION ALL\n".join(statements)
        + "\nORDER BY control_id\n"
    )


def validate_generated_sql(sql: str) -> tuple[str, ...]:
    without_comments = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    ).strip()
    if not without_comments:
        raise GeneratedSQLViolation("generated SQL is empty")
    if not re.match(r"^(SELECT|WITH)\b", without_comments, re.IGNORECASE):
        raise GeneratedSQLViolation("generated SQL must be a read-only SELECT")
    if _BANNED_SQL.search(without_comments):
        raise GeneratedSQLViolation("generated SQL contains a forbidden operation")
    if ";" in without_comments.rstrip(";"):
        raise GeneratedSQLViolation("generated SQL must contain exactly one statement")
    if "raw.orders" not in without_comments.casefold():
        raise GeneratedSQLViolation("generated SQL does not target the approved fixture table")
    referenced_tables = {
        match.casefold()
        for match in re.findall(
            r"\b(?:FROM|JOIN)\s+([a-z_][a-z0-9_.]*)",
            without_comments,
            re.IGNORECASE,
        )
    }
    if referenced_tables != {"raw.orders"}:
        raise GeneratedSQLViolation("generated SQL references an unapproved table")
    return (
        "single-statement",
        "read-only-select",
        "forbidden-operations-absent",
        "approved-table-only",
        "datahub-schema-bound",
        "campaign-gap-bound",
        "clean-profile-bound",
    )


def _required_column(parameters: dict[str, object], name: str) -> str:
    value = parameters.get(name)
    if not isinstance(value, str):
        raise GeneratedSQLViolation(f"campaign parameter {name} is not a column")
    _quoted_identifier(value)
    return value


def _quoted_identifier(value: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", value):
        raise GeneratedSQLViolation("generated control column is not a safe identifier")
    return f'"{value}"'


def _sha256_json(value: object) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
