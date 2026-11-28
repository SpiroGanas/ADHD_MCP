"""Screening history: one timeline from observation panels and questionnaire responses, with
the cutoff applied only when its code and value are verified.

``trusted`` content is built in the test from copies of the instruments marked verified,
so the cutoff logic can be tested; packaged content stays unverified.
"""

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from adhd_mcp.evidence.screening import (
    ScreeningContent,
    ScreeningHistoryResult,
    assemble_screening_history,
    load_screening_content,
)
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import DataStatus
from adhd_mcp.models.evidence_outputs import ScreeningEntry
from adhd_mcp.terminology.instruments import Instrument
from adhd_mcp.terminology.site_codes import load_site_codes, load_site_codes_file
from tests.helpers.failing_adapter import FailingAdapter
from tests.personas import all_resources
from tests.personas.builder import PersonaBuilder
from tests.personas.definitions import PHQ9_QUESTIONNAIRE

pytestmark = pytest.mark.anyio

AS_OF = date(2026, 6, 15)


def marked_verified(instrument: Instrument) -> Instrument:
    """A test-only copy with every code, cutoff and answer marked verified."""

    def mark(items: tuple[Any, ...]) -> tuple[Any, ...]:
        return tuple(
            i.model_copy(update={"verified": True, "source": "test", "source_version": "test"})
            for i in items
        )

    return instrument.model_copy(
        update={
            "codes": mark(instrument.codes),
            "cutoffs": mark(instrument.cutoffs),
            "answers": mark(instrument.answers),
        }
    )


def content(*, trusted: bool = False) -> ScreeningContent:
    packaged = load_screening_content(load_site_codes("synthetic"))
    if not trusted:
        return packaged
    return ScreeningContent(tuple(marked_verified(i) for i in packaged.instruments), packaged.site)


async def history(
    patient_id: str,
    resources: list[dict[str, Any]] | None = None,
    *,
    trusted: bool = False,
    as_of: date = AS_OF,
) -> ScreeningHistoryResult:
    records = PatientRecords(FixtureFhirAdapter(resources or all_resources()))
    patient = await records.patient(patient_id)
    return await assemble_screening_history(records, patient, as_of, content(trusted=trusted))


def summary(entries: list[ScreeningEntry]) -> list[tuple[Any, ...]]:
    return [(e.date, e.instrument, e.measure, e.item, e.score) for e in entries]


async def test_panel_form_timeline_for_p01() -> None:
    result = await history("p01-patient")
    assert summary(result.entries) == [
        (date(2025, 4, 1), "phq9", "item", "9", 0),
        (date(2025, 4, 1), "phq9", "total_score", None, 8),
    ]
    assert all(e.form == "observation" for e in result.entries)
    assert [r.id for r in result.entries[1].references] == ["p01-obs-2"]


async def test_questionnaire_form_for_p02() -> None:
    result = await history("p02-patient")
    assert summary(result.entries) == [
        (date(2025, 5, 20), "phq9", "item", "9", 0),
        (date(2025, 5, 20), "phq9", "total_score", None, 13),
        (date(2026, 1, 20), "auditc", "total_score", None, 3),
    ]
    phq9_total = result.entries[1]
    assert phq9_total.form == "questionnaire_response"
    assert phq9_total.code is not None
    assert phq9_total.code.code == "44261-6"
    assert phq9_total.code.display is None  # LOINC names repeat item wording; not returned


def same_values(entries: list[ScreeningEntry]) -> list[dict[str, Any]]:
    return [e.model_dump(exclude={"references", "form", "questionnaire"}) for e in entries]


async def test_panel_and_questionnaire_forms_give_the_same_timeline() -> None:
    panel = PersonaBuilder("t03", gender="female", birth_date="1990-01-01")
    item = panel.observation("44260-8", "PHQ-9 item 9", "2026-03-01T09:00:00Z", value=1)
    total = panel.observation("44261-6", "PHQ-9 total score", "2026-03-01T09:00:00Z", value=11)
    panel.observation("44249-1", "PHQ-9 panel", "2026-03-01T09:00:00Z", members=(item, total))
    form = PersonaBuilder("t04", gender="female", birth_date="1990-01-01")
    form.questionnaire_response(PHQ9_QUESTIONNAIRE, "2026-03-01", {"9": 1, "total": 11})
    a = await history(panel.patient_id, panel.resources)
    b = await history(form.patient_id, form.resources)
    assert len(a.entries) == 2
    assert same_values(a.entries) == same_values(b.entries)


async def test_entered_in_error_scores_are_not_listed() -> None:
    result = await history("p09-patient")
    assert summary(result.entries) == [(date(2024, 2, 1), "phq9", "total_score", None, 7)]


async def test_cssrs_risk_level_is_an_answer_not_a_score() -> None:
    result = await history("p03-patient")
    risk = next(e for e in result.entries if e.instrument == "cssrs_screener")
    assert (risk.measure, risk.score) == ("risk_level", None)
    assert risk.answer is not None
    assert (risk.answer.code, risk.answer.display) == ("LA9193-9", "High")


async def test_no_cutoff_is_applied_while_codes_and_cutoffs_are_unverified() -> None:
    result = await history("p10-patient")
    assert summary(result.entries) == [
        (date(2026, 4, 10), "auditc", "total_score", None, 1),
        (date(2026, 4, 10), "phq2", "total_score", None, 0),
    ]
    for entry in result.entries:
        assert entry.code_verified is False
        assert entry.cutoff is not None
        assert (entry.cutoff.status, entry.cutoff.met) == ("not_applied_unverified", None)
        # An unverified threshold is not shown at all.
        assert (entry.cutoff.operator, entry.cutoff.value, entry.cutoff.sex) == (None, None, None)


def auditc(gender: str, score: int) -> PersonaBuilder:
    p = PersonaBuilder("t05", gender=gender, birth_date="1990-01-01")
    p.observation("75626-2", "AUDIT-C total score", "2026-04-10T09:00:00Z", value=score)
    return p


@pytest.mark.parametrize(
    ("gender", "score", "met", "threshold"),
    [
        ("female", 2, False, 3),
        ("female", 3, True, 3),
        ("male", 3, False, 4),
        ("male", 4, True, 4),
    ],
)
async def test_audit_c_cutoffs_are_sex_specific(
    gender: str, score: int, met: bool, threshold: int
) -> None:
    p = auditc(gender, score)
    [entry] = (await history(p.patient_id, p.resources, trusted=True)).entries
    assert entry.cutoff is not None
    assert (entry.cutoff.status, entry.cutoff.met) == ("applied", met)
    assert (entry.cutoff.operator, entry.cutoff.value, entry.cutoff.sex) == (
        ">=",
        threshold,
        gender,
    )


async def test_sex_specific_cutoff_is_not_applied_when_sex_is_unknown() -> None:
    p = auditc("unknown", 5)
    [entry] = (await history(p.patient_id, p.resources, trusted=True)).entries
    assert entry.cutoff is not None
    assert (entry.cutoff.status, entry.cutoff.met) == ("not_applied_sex_unknown", None)


async def test_a_cutoff_for_any_sex_applies_to_everyone() -> None:
    p = PersonaBuilder("t06", gender="unknown", birth_date="1990-01-01")
    p.observation("55758-7", "PHQ-2 total score", "2026-04-10T09:00:00Z", value=3)
    [entry] = (await history(p.patient_id, p.resources, trusted=True)).entries
    assert entry.cutoff is not None
    assert (entry.cutoff.status, entry.cutoff.met, entry.cutoff.id) == ("applied", True, "positive")


async def test_a_measure_without_a_cutoff_says_so() -> None:
    entries = (await history("p03-patient", trusted=True)).entries
    [entry] = [e for e in entries if (e.instrument, e.measure) == ("phq9", "total_score")]
    assert entry.cutoff is None


async def test_an_unknown_instrument_is_reported_but_not_scored() -> None:
    p = PersonaBuilder("t07", gender="female", birth_date="1990-01-01")
    oid = p.observation("99999-9", "Synthetic unknown survey", "2026-04-10T09:00:00Z", value=12)
    p.questionnaire_response("urn:adhd-mcp:synthetic-questionnaire:other", "2026-04-11", {"1": 2})
    result = await history(p.patient_id, p.resources, trusted=True)
    first, second = result.entries
    assert (first.instrument, first.measure, first.score, first.cutoff) == (
        None,
        "unknown",
        12,
        None,
    )
    assert first.code is not None
    assert first.code.code == "99999-9"
    assert first.references[0].id == oid
    assert (second.instrument, second.form, second.score) == (None, "questionnaire_response", None)
    assert second.questionnaire == "urn:adhd-mcp:synthetic-questionnaire:other"


async def test_non_survey_observations_are_ignored() -> None:
    p = PersonaBuilder("t08", gender="female", birth_date="1990-01-01")
    oid = p.observation("8480-6", "Systolic blood pressure", "2026-04-10T09:00:00Z", value=120)
    next(r for r in p.resources if r["id"] == oid)["category"] = []
    assert (await history(p.patient_id, p.resources)).entries == []


async def test_entries_after_the_as_of_date_are_left_out() -> None:
    result = await history("p02-patient", as_of=date(2025, 5, 19))
    assert result.entries == []


async def test_undated_entries_come_last() -> None:
    p = PersonaBuilder("t09", gender="female", birth_date="1990-01-01")
    oid = p.observation("55758-7", "PHQ-2 total score", "2026-04-10T09:00:00Z", value=1)
    del next(r for r in p.resources if r["id"] == oid)["effectiveDateTime"]
    p.observation("75626-2", "AUDIT-C total score", "2026-04-10T09:00:00Z", value=1)
    result = await history(p.patient_id, p.resources)
    assert [e.instrument for e in result.entries] == ["auditc", "phq2"]
    assert result.entries[1].date is None


async def test_cancelled_observations_are_left_out() -> None:
    p = PersonaBuilder("t10", gender="female", birth_date="1990-01-01")
    p.observation("55758-7", "PHQ-2", "2026-04-10T09:00:00Z", value=1, status="cancelled")
    assert (await history(p.patient_id, p.resources)).entries == []


async def test_failed_categories_are_reported() -> None:
    p = PersonaBuilder("t11", gender="female", birth_date="1990-01-01")
    records = PatientRecords(FailingAdapter(p, {"QuestionnaireResponse"}))
    patient = await records.patient(p.patient_id)
    result = await assemble_screening_history(records, patient, AS_OF, content())
    statuses = {n.category: n.status for n in result.data_completeness}
    assert statuses == {"Observation": DataStatus.EMPTY, "QuestionnaireResponse": DataStatus.FAILED}


async def test_instruments_checked_lists_every_instrument() -> None:
    result = await history("p07-patient")
    assert result.instruments_checked == [
        "asrs5",
        "auditc",
        "cssrs_screener",
        "pcptsd5",
        "phq2",
        "phq9",
    ]


async def test_a_questionnaire_without_a_total_lists_only_its_items() -> None:
    p = PersonaBuilder("t12", gender="female", birth_date="1990-01-01")
    p.questionnaire_response(PHQ9_QUESTIONNAIRE, "2026-03-01", {"9": 2})
    result = await history(p.patient_id, p.resources)
    assert summary(result.entries) == [(date(2026, 3, 1), "phq9", "item", "9", 2)]


async def test_a_questionnaire_for_an_instrument_without_codes_is_listed_unscored(
    tmp_path: Path,
) -> None:
    path = tmp_path / "asrs_site.toml"
    path.write_text(
        'id = "asrs_site"\nversion = "1"\ntitle = "t"\n'
        "[[questionnaires]]\n"
        'url = "urn:adhd-mcp:synthetic-questionnaire:asrs-5"\n'
        'instrument = "asrs5"\ntotal = "total"\nverified = true\n'
    )
    p = PersonaBuilder("t13", gender="female", birth_date="1990-01-01")
    qid = p.questionnaire_response(
        "urn:adhd-mcp:synthetic-questionnaire:asrs-5", "2026-03-01", {"total": 16}
    )
    records = PatientRecords(FixtureFhirAdapter(p.resources))
    patient = await records.patient(p.patient_id)
    site_content = load_screening_content(load_site_codes_file(path, strict=True))
    result = await assemble_screening_history(records, patient, AS_OF, site_content)
    [entry] = result.entries
    assert (entry.instrument, entry.measure, entry.score) == ("asrs5", "total_score", 16)
    assert (entry.code, entry.code_verified, entry.cutoff) == (None, False, None)
    assert entry.references[0].id == qid


async def test_a_verified_cutoff_without_a_score_is_not_applied() -> None:
    p = PersonaBuilder("t14", gender="female", birth_date="1990-01-01")
    oid = p.observation("55758-7", "PHQ-2 total score", "2026-04-10T09:00:00Z", value=1)
    resource = next(r for r in p.resources if r["id"] == oid)
    del resource["valueQuantity"]
    resource["valueString"] = "synthetic text"
    [entry] = (await history(p.patient_id, p.resources, trusted=True)).entries
    assert entry.cutoff is not None
    assert (entry.cutoff.status, entry.cutoff.met) == ("not_applied_no_score", None)
