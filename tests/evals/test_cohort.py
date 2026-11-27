"""The labelled cohort (Phase 7, item 1): its design, and every patient's outcome against the
expectation written by hand for its archetype."""

from collections import Counter

import pytest

from adhd_mcp.rules.catalog import load_catalog
from tests.evals import harness as h
from tests.evals.cohort import AGE_BANDS, ARCHETYPES, SEXES, build_cohort
from tests.personas.builder import HTEST, SYNTHETIC_ID

pytestmark = pytest.mark.anyio

COHORT = build_cohort()


def test_size_is_in_the_planned_range() -> None:
    assert 100 <= len(COHORT) <= 200


def test_balanced_by_sex_and_age_band() -> None:
    cells = Counter((p.archetype.id, p.sex, p.age_band) for p in COHORT)
    assert set(cells.values()) == {1}
    assert len(cells) == len(ARCHETYPES) * len(SEXES) * len(AGE_BANDS)


def test_includes_look_alikes_and_sparse_records() -> None:
    titles = " ".join(a.title for a in ARCHETYPES if a.profile == "not_suggestive")
    for look_alike in ("TBI", "PTSD", "Bipolar", "Substance use without ADHD signals", "Sparse"):
        assert look_alike in titles
    assert any(a.recommendation == "insufficient_data" for a in ARCHETYPES)


def test_both_presentation_styles_are_represented() -> None:
    styles = Counter(a.style for a in ARCHETYPES if a.profile == "suggestive")
    assert styles["externalizing"] >= 3
    assert styles["internalizing"] >= 3
    assert all((a.style is None) == (a.profile != "suggestive") for a in ARCHETYPES)


def test_every_catalog_signal_and_recommendation_is_exercised() -> None:
    signals = {s for a in ARCHETYPES for s in a.signals}
    assert {s.id for s in load_catalog("adhd_mcp.data.adhd").signals} <= signals
    assert {a.recommendation for a in ARCHETYPES} == {
        "consider_referral_for_formal_screening",
        "no_recommendation",
        "address_safety_gate_first",
        "already_in_care",
        "insufficient_data",
    }


def test_every_patient_is_obviously_synthetic_and_ids_are_unique() -> None:
    ids = [r["id"] for p in COHORT for r in p.resources]
    assert len(ids) == len(set(ids))
    for p in COHORT:
        patient = p.resources[0]
        assert patient["meta"]["tag"] == [HTEST]
        assert patient["identifier"][0]["system"] == SYNTHETIC_ID
        assert patient["name"][0]["family"] == "Synthetic"


def test_the_cohort_is_deterministic() -> None:
    again = build_cohort()
    assert [p.resources for p in again] == [p.resources for p in COHORT]


def test_copies_of_an_archetype_differ() -> None:
    e1 = [p for p in COHORT if p.archetype.id == "E1"]
    codes = {
        tuple(
            r["code"]["coding"][0]["code"] for r in p.resources if r["resourceType"] == "Condition"
        )
        for p in e1
    }
    assert len(codes) > 1


async def test_every_patient_matches_its_archetypes_intended_outcome() -> None:
    out = h.agreement(await h.run_cohort(COHORT))
    assert out["mismatches"] == []
    assert out["agree"] == len(COHORT)
