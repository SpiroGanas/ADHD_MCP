"""ADHD, the first condition plugin: its catalog, ruleset, wording and exclusions."""

import asyncio
from datetime import date, timedelta
from functools import cache

from adhd_mcp.conditions.base import ConditionPlugin, ExclusionResult
from adhd_mcp.evidence.existing_care import (
    ExistingCareContent,
    assemble_existing_care,
    load_existing_care_content,
)
from adhd_mcp.evidence.medication_timeline import (
    MedicationTimelineResult,
    assemble_medication_timeline,
    load_medication_content,
)
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import CheckOutcome, DataStatus, ExclusionCheck
from adhd_mcp.rules.catalog import load_catalog
from adhd_mcp.rules.ruleset import load_ruleset
from adhd_mcp.rules.scorer import RulesOnlyScorer
from adhd_mcp.terminology.site_codes import SiteCodes
from adhd_mcp.wording import load_wording

DATA = "adhd_mcp.data.adhd"


_MEDICATION_CHECK = "adhd_medication_exposure"


def _medication_check(
    content: ExistingCareContent, timeline: MedicationTimelineResult, as_of: date
) -> ExclusionCheck:
    """Peer review 01, C4: recent exposure to an ADHD medication, not for narcolepsy."""
    d = content.definition
    description = (
        f"ADHD medication dispensed or taken within {d.adhd_medication_recent_days} days, "
        "not for narcolepsy"
    )
    unreadable = [
        n.category
        for n in timeline.data_completeness
        if n.status in (DataStatus.FAILED, DataStatus.INCOMPLETE)
    ]
    since = as_of - timedelta(days=d.adhd_medication_recent_days)
    recent = [
        x
        for x in timeline.exposures
        if x.drug_class in d.adhd_medication_classes and not x.for_narcolepsy and x.end >= since
    ]
    if recent:
        refs = sorted(
            {r for x in recent for r in x.references}, key=lambda r: (r.resource_type, r.id)
        )
        return ExclusionCheck(
            check=_MEDICATION_CHECK,
            description=description,
            outcome=CheckOutcome.FOUND,
            references=refs,
        )
    if unreadable:
        return ExclusionCheck(
            check=_MEDICATION_CHECK,
            description=description,
            outcome=CheckOutcome.FAILED,
            reason=f"Could not read {', '.join(unreadable)} completely",
        )
    return ExclusionCheck(
        check=_MEDICATION_CHECK, description=description, outcome=CheckOutcome.NOT_FOUND
    )


async def adhd_exclusions(
    records: PatientRecords, patient_id: str, as_of: date, site: SiteCodes
) -> ExclusionResult:
    content = load_existing_care_content(site)
    care, timeline = await asyncio.gather(
        assemble_existing_care(records, patient_id, as_of, content),
        assemble_medication_timeline(records, patient_id, as_of, load_medication_content()),
    )
    notes = []
    wording = load_wording()
    medication = _medication_check(content, timeline, as_of)
    excluded = care.excluded
    hold = False
    if medication.outcome is CheckOutcome.FOUND and excluded is not True:
        # Current ADHD medication without an ADHD code: perhaps in care elsewhere (C4).
        excluded, hold = None, True
        notes.append(wording.notes["adhd_medication_without_code"])
    elif care.excluded is None:
        notes.append(wording.notes["exclusions_incomplete"])
    if care.narcolepsy is not None and care.narcolepsy.medication_for_narcolepsy:
        notes.append(wording.notes["narcolepsy_medication"])
    return ExclusionResult(
        excluded=excluded,
        checks=[*care.exclusions_checked, medication],
        data_completeness=[*care.data_completeness, *timeline.data_completeness],
        notes=notes,
        hold=hold,
    )


@cache
def adhd_plugin() -> ConditionPlugin:
    wording = load_wording()
    return ConditionPlugin(
        id="adhd",
        title="ADHD",
        catalog=load_catalog(DATA),
        ruleset=load_ruleset(DATA),
        recommendation_texts=wording.recommendations,
        next_step=wording.adhd_next_step,
        note_texts={"tbi_overlap": wording.notes["tbi_overlap"]},
        exclusions=adhd_exclusions,
        scorer=RulesOnlyScorer(),
    )
