"""ADHD, the first condition plugin: its catalog, ruleset, wording and exclusions."""

from datetime import date
from functools import cache

from adhd_mcp.conditions.base import ConditionPlugin, ExclusionResult
from adhd_mcp.evidence.existing_care import assemble_existing_care, load_existing_care_content
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.rules.catalog import load_catalog
from adhd_mcp.rules.ruleset import load_ruleset
from adhd_mcp.rules.scorer import RulesOnlyScorer
from adhd_mcp.terminology.site_codes import SiteCodes
from adhd_mcp.wording import load_wording

DATA = "adhd_mcp.data.adhd"


async def adhd_exclusions(
    records: PatientRecords, patient_id: str, as_of: date, site: SiteCodes
) -> ExclusionResult:
    care = await assemble_existing_care(
        records, patient_id, as_of, load_existing_care_content(site)
    )
    notes = []
    wording = load_wording()
    if care.excluded is None:
        notes.append(wording.notes["exclusions_incomplete"])
    if care.narcolepsy is not None and care.narcolepsy.medication_for_narcolepsy:
        notes.append(wording.notes["narcolepsy_medication"])
    return ExclusionResult(
        excluded=care.excluded,
        checks=care.exclusions_checked,
        data_completeness=care.data_completeness,
        notes=notes,
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
