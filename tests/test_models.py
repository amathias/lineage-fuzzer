from __future__ import annotations

import pytest
from pydantic import ValidationError

from lineage_fuzzer.domain.models import CampaignManifest, FaultKind, FaultSpecification
from tests.factories import make_manifest, make_target


def test_manifest_digest_is_reproducible_across_creation_timestamps() -> None:
    first = make_manifest()
    second = CampaignManifest(**{**first.model_dump(), "created_at": "2026-07-25T00:00:00Z"})

    assert first.sha256 == second.sha256


def test_manifest_digest_changes_with_seed() -> None:
    first = make_manifest()
    second = CampaignManifest(**{**first.model_dump(), "seed": first.seed + 1})

    assert first.sha256 != second.sha256


def test_manifest_rejects_fault_for_unknown_target() -> None:
    target = make_target()
    with pytest.raises(ValidationError, match="absent from manifest"):
        CampaignManifest(
            seed=1,
            graph_snapshot_sha256="b" * 64,
            targets=(target,),
            faults=(
                FaultSpecification(
                    fault_id="unknown-target",
                    kind=FaultKind.STALE_PARTITION,
                    target_urn="urn:li:dataset:unknown",
                    restore_action="restore_snapshot",
                ),
            ),
        )
