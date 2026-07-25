from __future__ import annotations

import hashlib
import re
from pathlib import Path

import duckdb

from lineage_fuzzer.campaign.models import GeneratedControlArtifact
from lineage_fuzzer.pipeline.fixture import CommerceFixture
from lineage_fuzzer.pipeline.models import ControlDefinition

GENERATED_CONTROLS = (
    ControlDefinition(
        control_id="orders_amount_cents_reasonable",
        description="Raw order amounts must remain within the seeded business range.",
        target_table="raw.orders",
        violation_query=(
            "SELECT count(*) FROM raw.orders WHERE amount_cents > 125000"
        ),
        detects_faults=("numeric_scale",),
    ),
    ControlDefinition(
        control_id="orders_partition_not_stale",
        description="Raw order partitions must not predate the deterministic fixture window.",
        target_table="raw.orders",
        violation_query=(
            "SELECT count(*) FROM raw.orders "
            "WHERE source_partition < DATE '2026-07-01'"
        ),
        detects_faults=("stale_partition",),
    ),
)

ARTIFACT_FILENAME = "lineage_fuzzer_generated_controls.sql"

_BANNED_SQL = re.compile(
    r"\b("
    r"ALTER|ATTACH|CALL|COPY|CREATE|DELETE|DETACH|DROP|EXECUTE|EXPORT|"
    r"IMPORT|INSERT|INSTALL|LOAD|MERGE|PRAGMA|SET|TRUNCATE|UPDATE|VACUUM"
    r")\b",
    re.IGNORECASE,
)


class GeneratedSQLViolation(RuntimeError):
    """Raised when generated SQL is not one bounded read-only query."""


class GeneratedControlService:
    """Render, validate, and execute deterministic metadata-grounded SQL controls."""

    def __init__(self, artifact_root: Path) -> None:
        self.artifact_root = artifact_root.resolve(strict=False)

    @property
    def artifact_path(self) -> Path:
        return (self.artifact_root / ARTIFACT_FILENAME).resolve(strict=False)

    def generate_and_validate(self, fixture: CommerceFixture) -> GeneratedControlArtifact:
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        path = self.artifact_path
        if self.artifact_root not in path.parents:
            raise GeneratedSQLViolation("generated artifact path escaped its output root")

        sql = render_generated_control_sql()
        policy_checks = validate_generated_sql(sql)
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(sql, encoding="utf-8", newline="\n")
        temporary.replace(path)

        clean_violations = self.execute(path, fixture)
        clean_execution_passed = all(value == 0 for value in clean_violations.values())
        if not clean_execution_passed:
            raise GeneratedSQLViolation("generated controls failed against the clean fixture")
        return GeneratedControlArtifact(
            path=Path(ARTIFACT_FILENAME),
            sha256=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
            control_ids=tuple(control.control_id for control in GENERATED_CONTROLS),
            policy_checks=policy_checks,
            clean_violations=clean_violations,
            clean_execution_passed=True,
        )

    def execute(self, path: Path, fixture: CommerceFixture) -> dict[str, int]:
        resolved = path.resolve(strict=True)
        if self.artifact_root not in resolved.parents:
            raise GeneratedSQLViolation("generated artifact execution escaped its output root")
        sql = resolved.read_text(encoding="utf-8")
        validate_generated_sql(sql)
        with duckdb.connect(str(fixture.database_path), read_only=True) as connection:
            rows = connection.execute(sql).fetchall()
        result = {str(row[0]): int(row[1]) for row in rows}
        expected = {control.control_id for control in GENERATED_CONTROLS}
        if set(result) != expected:
            raise GeneratedSQLViolation("generated artifact returned unexpected control IDs")
        if any(value < 0 for value in result.values()):
            raise GeneratedSQLViolation("generated artifact returned a negative violation count")
        return dict(sorted(result.items()))


def render_generated_control_sql() -> str:
    return """-- Generated deterministically from the raw.orders schema and campaign gaps.
-- Read-only DuckDB test artifact; zero violations means the control passes.
SELECT
    'orders_amount_cents_reasonable' AS control_id,
    count(*)::BIGINT AS violation_count
FROM raw.orders
WHERE amount_cents > 125000
UNION ALL
SELECT
    'orders_partition_not_stale' AS control_id,
    count(*)::BIGINT AS violation_count
FROM raw.orders
WHERE source_partition < DATE '2026-07-01'
ORDER BY control_id
"""


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
    )
