import pytest

from adhd_mcp.wording import load_wording
from adhd_mcp.wording.guard import find_diagnostic_language
from tests.helpers.wording import assert_no_diagnostic_language

DIAGNOSTIC_SENTENCES = [
    "The patient has ADHD.",
    "Veteran likely has adult ADHD.",
    "Findings are consistent with ADHD.",
    "This record is indicative of attention-deficit/hyperactivity disorder.",
    "Diagnosis: ADHD",
    "The patient meets criteria for ADHD.",
    "This result is a diagnosis of ADHD.",
    "Probable ADHD.",
    "ADHD confirmed.",
    "The patient is positive for ADHD.",
    "He suffers from ADHD.",
    "The patient is diagnosed with ADHD by this assessment.",
    # Phrasings found missing in the Phase 1-2 safety review:
    "The patient has undiagnosed ADHD.",
    "The patient has possible ADHD.",
    "The patient has adult-onset ADHD.",
    "ADHD is likely.",
    "ADHD suspected.",
    "Presentation suggests ADHD.",
    "Veteran with ADHD.",
    "Patient diagnosed with ADHD.",
    "Diagnosis - ADHD",
    "High probability of ADHD.",
    "The patient has ADD.",
    "Shows signs of ADHD.",
    # Other conditions and suicide-risk statements:
    "The patient has PTSD.",
    "Veteran with bipolar disorder.",
    "The patient has depression.",
    "Patient is suicidal.",
    "The veteran is at high risk of suicide.",
    "Patient is at low risk for suicide.",
]

ACCEPTABLE_SENTENCES = [
    "Consider referral for formal ADHD screening.",
    "No existing ADHD diagnosis was found in the record.",
    "An ADHD diagnosis code is recorded; the patient is already in care.",
    "PHQ-9 item 9 screen positive on 2025-01-02.",
    "It is not a diagnosis.",
    "This tool never diagnoses.",
    "A PTSD code (F43.10) is recorded in Condition/p09-cond-1.",
    "Stimulant-related disorder code recorded.",
    "No evidence of an existing ADHD diagnosis was found.",
    "Suicidal ideation code recorded; complete a suicide risk evaluation first.",
    "Consider an ASRS screen; add the result to the record.",
    "The patient has added a new address.",
]


@pytest.mark.parametrize("sentence", DIAGNOSTIC_SENTENCES)
def test_guard_flags_diagnostic_language(sentence: str) -> None:
    assert find_diagnostic_language(sentence), sentence


@pytest.mark.parametrize("sentence", ACCEPTABLE_SENTENCES)
def test_guard_passes_acceptable_language(sentence: str) -> None:
    assert find_diagnostic_language(sentence) == []


def test_guard_passes_the_approved_wording() -> None:
    wording = load_wording()
    assert find_diagnostic_language(wording.approved_recommendation) == []
    assert find_diagnostic_language(wording.standard_notice) == []


def test_helper_walks_nested_output() -> None:
    output = {"basis": [{"signal": "x", "note": "Findings are consistent with ADHD."}]}
    with pytest.raises(AssertionError, match=r"basis\[0\]\.note"):
        assert_no_diagnostic_language(output)


def test_helper_rejects_a_true_is_diagnosis_marker() -> None:
    with pytest.raises(AssertionError, match="is_diagnosis"):
        assert_no_diagnostic_language({"is_diagnosis": True})


def test_helper_checks_dictionary_keys() -> None:
    with pytest.raises(AssertionError):
        assert_no_diagnostic_language({"Patient has ADHD": 1})


def test_helper_passes_clean_output() -> None:
    assert_no_diagnostic_language(
        {"is_diagnosis": False, "items": ["Consider referral for formal ADHD screening.", 3, None]}
    )
