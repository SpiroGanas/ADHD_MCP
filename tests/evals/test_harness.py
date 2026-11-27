"""The harness on a tiny fixed cohort reproduces a report worked out by hand (Phase 7,
item 2, "tests first")."""

import dataclasses

import pytest

from adhd_mcp.conditions.adhd import adhd_plugin
from tests.evals import harness as h
from tests.evals.cohort import ARCHETYPES, CONSIDER, CohortPatient, build_patient

pytestmark = pytest.mark.anyio

BY_ID = {a.id: a for a in ARCHETYPES}


def tiny_cohort() -> list[CohortPatient]:
    """Five patients whose outcomes under ruleset 1.0.0 are known by hand:

    c001 E2 female 18-29  alcohol + PTSD + legal       -> consider (high_with_modifiers)
    c002 I1 female 30-44  four modifiers, no high      -> no_recommendation
    c003 L5 male   18-29  alcohol alone                -> no_recommendation
    c004 G1 male   45-64  ideation code, two highs     -> address_safety_gate_first
    c005 E3 male   30-44  two injuries + stimulant     -> consider (two_high_classes)
    """
    rows = [
        ("E2", "female", "18-29"),
        ("I1", "female", "30-44"),
        ("L5", "male", "18-29"),
        ("G1", "male", "45-64"),
        ("E3", "male", "30-44"),
    ]
    return [
        build_patient(BY_ID[a], sex, band, index, variant)
        for variant, (index, (a, sex, band)) in enumerate(enumerate(rows, start=1))
    ]


@pytest.fixture
async def results() -> list[h.PatientResult]:
    return await h.run_cohort(tiny_cohort())


async def test_agreement(results: list[h.PatientResult]) -> None:
    out = h.agreement(results)
    assert (out["patients"], out["agree"], out["mismatches"]) == (5, 5, [])
    assert out["by_field"] == dict.fromkeys(h.FIELDS, 5)


async def test_a_wrong_expectation_is_reported_as_a_mismatch() -> None:
    patients = tiny_cohort()
    wrong = dataclasses.replace(BY_ID["L5"], recommendation=CONSIDER)
    patients[2] = dataclasses.replace(patients[2], archetype=wrong)
    out = h.agreement(await h.run_cohort(patients))
    assert (out["agree"], out["by_field"]["recommendation"]) == (4, 4)
    assert out["mismatches"] == [
        {
            "patient_id": "c003-patient",
            "archetype": "L5",
            "field": "recommendation",
            "expected": CONSIDER,
            "actual": "no_recommendation",
        }
    ]


async def test_recommendation_counts_and_rates(results: list[h.PatientResult]) -> None:
    assert h.recommendation_counts(results) == {
        "address_safety_gate_first": 1,
        CONSIDER: 2,
        "no_recommendation": 2,
    }
    by_sex = h.rates_by(results, lambda r: r.patient.sex)
    assert {k: (v["flagged"], v["total"], v["rate"]) for k, v in by_sex.items()} == {
        "female": (1, 2, 0.5),
        "male": (1, 3, 0.333),
    }
    by_age = h.rates_by(results, lambda r: r.patient.age_band)
    assert {k: (v["flagged"], v["total"]) for k, v in by_age.items()} == {
        "18-29": (1, 2),
        "30-44": (1, 2),
        "45-64": (0, 1),
    }


async def test_drivers(results: list[h.PatientResult]) -> None:
    assert h.drivers(results) == {
        "flagged": 2,
        "signals": {
            "alcohol_involvement": 1,
            "legal_problems": 1,
            "ptsd": 1,
            "repeated_accidental_injury": 1,
            "stimulant_related_disorder": 1,
        },
        "rules": {"high_with_modifiers": 1, "two_high_classes": 1},
    }


async def test_profiles_styles_and_the_mix(results: list[h.PatientResult]) -> None:
    def short(groups: dict[str, dict[str, object]]) -> dict[str, tuple[object, ...]]:
        return {k: (v["flagged"], v["total"], v["rate"]) for k, v in groups.items()}

    assert short(h.by_profile(results)) == {
        "not_applicable": (0, 1, 0.0),
        "not_suggestive": (0, 1, 0.0),
        "suggestive": (2, 3, 0.667),
    }
    style = h.suggestive_by_style(results)
    assert short(style) == {"externalizing": (2, 2, 1.0), "internalizing": (0, 1, 0.0)}
    assert short(h.suggestive_by_sex(results)) == {
        "female": (1, 2, 0.5),
        "male": (1, 1, 1.0),
    }
    # female: 0.7 x 0.0 + 0.3 x 1.0; male: 0.3 x 0.0 + 0.7 x 1.0
    assert h.mixed_recall(style, h.MIX) == {"female": 0.3, "male": 0.7}


def test_mixed_recall_needs_every_style() -> None:
    assert h.mixed_recall({"externalizing": {"rate": 1.0}}, h.MIX) == {
        "female": None,
        "male": None,
    }


async def test_a_four_modifier_rule_flags_the_internalizing_case(
    results: list[h.PatientResult],
) -> None:
    option = next(v for v in h.OPTIONS if v.id == "add_four_modifiers")
    variant = await h.run_cohort(tiny_cohort(), option.apply(adhd_plugin()))
    out = h.changes(results, variant)
    assert (out["flagged"], out["changed"]) == (3, 1)
    assert out["newly_flagged"] == {"I1": 1}
    assert out["no_longer_flagged"] == {}
    assert out["suggestive"]["rate"] == 1.0
    assert out["not_suggestive"]["rate"] == 0.0
    assert out["mixed_recall"] == {"female": 1.0, "male": 1.0}


async def test_raising_two_high_classes_to_three_drops_the_two_injury_case(
    results: list[h.PatientResult],
) -> None:
    variant_def = next(v for v in h.SENSITIVITY if v.id == "thc_min_high_3")
    variant = await h.run_cohort(tiny_cohort(), variant_def.apply(adhd_plugin()))
    out = h.changes(results, variant)
    assert (out["flagged"], out["changed"]) == (1, 1)
    assert out["no_longer_flagged"] == {"E3": 1}


def test_variants_leave_the_loaded_ruleset_untouched() -> None:
    before = adhd_plugin().ruleset
    for v in (*h.SENSITIVITY, *h.OPTIONS):
        v.apply(adhd_plugin())
    assert adhd_plugin().ruleset == before
    assert len({v.id for v in h.SENSITIVITY}) == len(h.SENSITIVITY)
