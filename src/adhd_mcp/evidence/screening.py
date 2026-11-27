"""Screening history: instrument scores from Observations and QuestionnaireResponses.

Observations are read as panels, standalone results or components; questionnaire responses
through the site's questionnaire mapping. Both forms produce the same entries. Instruments
are recognised by their codes even while those are unverified, so the clinician sees the
record; each entry says whether its code is verified. A cutoff is applied only when both the
code and the cutoff are verified (standing invariant 6), and a sex-specific cutoff only when
the patient's administrative sex is recorded as male or female.
"""

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Literal

from adhd_mcp.evidence.common import completeness, not_after, read_category
from adhd_mcp.fhir.codes import Coding
from adhd_mcp.fhir.dates import DateRange
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.fhir.records import (
    ObservationRecord,
    PatientRecord,
    QuestionnaireResponseRecord,
    Value,
)
from adhd_mcp.models.domain import DataCompleteness, ResourceRef
from adhd_mcp.models.evidence_outputs import CodeRef, CutoffResult, ScreeningEntry
from adhd_mcp.terminology.instruments import (
    Instrument,
    InstrumentCode,
    load_instrument,
    packaged_instrument_ids,
)
from adhd_mcp.terminology.site_codes import SiteCodes

_NO_RESULT = frozenset({"registered", "cancelled", "entered-in-error"})
_SURVEY = "survey"
Measure = Literal["total_score", "item", "risk_level"]
Form = Literal["observation", "questionnaire_response"]
_MEASURES: dict[str, Measure] = {
    "total_score": "total_score",
    "item": "item",
    "risk_level": "risk_level",
}


@dataclass(frozen=True)
class ScreeningContent:
    instruments: tuple[Instrument, ...]
    site: SiteCodes
    trust_unverified: bool = False


def load_screening_content(site: SiteCodes, *, trust_unverified: bool = False) -> ScreeningContent:
    """Instruments are loaded for recognition only. ``trust_unverified`` exists for tests of
    the cutoff logic; the server never sets it."""
    instruments = tuple(load_instrument(i, strict=False) for i in packaged_instrument_ids())
    return ScreeningContent(instruments, site, trust_unverified)


@dataclass(frozen=True)
class ScreeningHistoryResult:
    entries: list[ScreeningEntry]
    instruments_checked: list[str]
    data_completeness: list[DataCompleteness]


def _code_ref(coding: Coding | InstrumentCode) -> CodeRef:
    """No display: instrument LOINC names can repeat copyrighted item wording."""
    return CodeRef(system=coding.system, code=coding.code)


def _cutoff(
    instrument: Instrument,
    code: InstrumentCode,
    score: float | None,
    sex: str | None,
    trust: bool,
) -> CutoffResult | None:
    cutoffs = [c for c in instrument.cutoffs if c.code == code.code]
    if not cutoffs:
        return None
    chosen = next((c for c in cutoffs if c.sex == "any"), None)
    chosen = chosen or next((c for c in cutoffs if c.sex == sex), None)
    if chosen is None:
        c = cutoffs[0]
        return CutoffResult(
            id=c.id,
            operator=c.operator,
            value=c.value,
            sex=c.sex,
            status="not_applied_sex_unknown",
            met=None,
            note=c.note,
        )
    verified = trust or (chosen.verified and code.verified)
    applied = verified and score is not None
    return CutoffResult(
        id=chosen.id,
        operator=chosen.operator,
        value=chosen.value,
        sex=chosen.sex,
        status="applied" if applied else "not_applied_unverified",
        met=chosen.is_met(score) if applied and score is not None else None,
        note=chosen.note,
    )


def _entry(
    instrument: Instrument,
    code: InstrumentCode,
    value: Value | None,
    when: DateRange | None,
    *,
    form: Form,
    reference: ResourceRef,
    sex: str | None,
    trust: bool,
    questionnaire: str | None = None,
) -> ScreeningEntry:
    score = value.number if value is not None else None
    answer = _code_ref(value.codings[0]) if value is not None and value.codings else None
    return ScreeningEntry(
        instrument=instrument.id,
        instrument_title=instrument.title,
        measure=_MEASURES[code.role],
        item=code.item,
        date=when.start if when is not None else None,
        score=score,
        answer=answer,
        code=_code_ref(code),
        code_verified=code.verified or trust,
        form=form,
        questionnaire=questionnaire,
        cutoff=_cutoff(instrument, code, score, sex, trust),
        references=[reference],
    )


def _measure_codes(
    instruments: Iterable[Instrument],
) -> dict[tuple[str, str], tuple[Instrument, InstrumentCode]]:
    return {(c.system, c.code): (i, c) for i in instruments for c in i.codes if c.role in _MEASURES}


def _panel_codes(instruments: Iterable[Instrument]) -> set[tuple[str, str]]:
    return {(c.system, c.code) for i in instruments for c in i.codes if c.role == "panel"}


def _from_observation(
    o: ObservationRecord, content: ScreeningContent, sex: str | None
) -> list[ScreeningEntry]:
    measures = _measure_codes(content.instruments)
    panels = _panel_codes(content.instruments)
    found: list[ScreeningEntry] = []
    parts = [(o.codes, o.value)] + [(c.codes, c.value) for c in o.components]
    for codes, value in parts:
        for coding in codes:
            match = measures.get((coding.system or "", coding.code))
            if match is not None:
                instrument, code = match
                found.append(
                    _entry(
                        instrument,
                        code,
                        value,
                        o.effective,
                        form="observation",
                        reference=o.ref,
                        sex=sex,
                        trust=content.trust_unverified,
                    )
                )
                break
    is_survey = any(c.code == _SURVEY for c in o.categories)
    is_panel = any((c.system or "", c.code) in panels for c in o.codes)
    if found or is_panel or not is_survey or not o.codes:
        return found
    return [
        ScreeningEntry(
            instrument=None,
            instrument_title=None,
            measure="unknown",
            date=o.effective.start if o.effective else None,
            score=o.value.number if o.value else None,
            code=_code_ref(o.codes[0]),
            code_verified=False,
            form="observation",
            cutoff=None,
            references=[o.ref],
        )
    ]


def _from_response(
    r: QuestionnaireResponseRecord, content: ScreeningContent, sex: str | None
) -> list[ScreeningEntry]:
    mapping = content.site.questionnaire(r.questionnaire)
    instrument = next(
        (i for i in content.instruments if mapping and i.id == mapping.instrument), None
    )
    if mapping is None or instrument is None:
        return [
            ScreeningEntry(
                instrument=None,
                instrument_title=None,
                measure="unknown",
                date=r.authored.start if r.authored else None,
                score=None,
                code=None,
                code_verified=False,
                form="questionnaire_response",
                questionnaire=r.questionnaire,
                cutoff=None,
                references=[r.ref],
            )
        ]
    answers = {i.link_id: i.answers for i in r.items}
    wanted = [("total_score", None, mapping.total)] + [
        ("item", item, link) for item, link in mapping.items.items()
    ]
    found = []
    for role, item, link_id in wanted:
        values = answers.get(link_id or "")
        if not values:
            continue
        code = next(c for c in instrument.codes if c.role == role and c.item == item)
        found.append(
            _entry(
                instrument,
                code,
                values[0],
                r.authored,
                form="questionnaire_response",
                reference=r.ref,
                sex=sex,
                trust=content.trust_unverified,
                questionnaire=r.questionnaire,
            )
        )
    return found


def _sort_key(e: ScreeningEntry) -> tuple[bool, date, str, str, str]:
    return (e.date is None, e.date or date.min, e.instrument or "~", e.measure, e.item or "")


async def assemble_screening_history(
    records: PatientRecords, patient: PatientRecord, as_of: date, content: ScreeningContent
) -> ScreeningHistoryResult:
    """``patient`` supplies the administrative sex for sex-specific cutoffs."""
    patient_id = patient.ref.id
    sex = (
        patient.administrative_gender
        if patient.administrative_gender in {"male", "female"}
        else None
    )
    observations, responses = await asyncio.gather(
        read_category(records.observations(patient_id)),
        read_category(records.questionnaire_responses(patient_id)),
    )
    entries: list[ScreeningEntry] = []
    for o in observations.records if observations else ():
        if o.status not in _NO_RESULT and not_after(o.effective, as_of):
            entries += _from_observation(o, content, sex)
    for r in responses.records if responses else ():
        if not_after(r.authored, as_of):
            entries += _from_response(r, content, sex)
    entries.sort(key=_sort_key)
    return ScreeningHistoryResult(
        entries=entries,
        instruments_checked=[i.id for i in content.instruments],
        data_completeness=[
            completeness("Observation", observations),
            completeness("QuestionnaireResponse", responses),
        ],
    )
