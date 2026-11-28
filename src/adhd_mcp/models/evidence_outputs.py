"""Output schemas of the evidence tools. Fixed by contract snapshots."""

import datetime as dt
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from adhd_mcp.models.domain import (
    DataCompleteness,
    ExclusionCheck,
    PrivacyNote,
    ResourceRef,
    SafetyGateResult,
    Versions,
)


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CodeRef(_Frozen):
    system: str | None
    code: str
    display: str | None = None


class ProblemEntry(_Frozen):
    code: CodeRef
    onset: date | None = Field(description="Earliest onset date recorded, if any")
    first_recorded: date | None = Field(description="Earliest recorded date, if any")
    last_recorded: date | None = Field(description="Latest recorded date, if any")
    last_date: date | None = Field(
        default=None,
        description="Latest date any record of this code carries (recorded, onset or "
        "abatement), if any",
    )
    clinical_status: str | None = Field(description="Clinical status of the latest record")
    resolved: bool = Field(description="True when the latest record is resolved or inactive")
    current: bool = Field(
        default=False,
        description="True when the latest record is an active problem-list item with no "
        "abatement on or before the as-of date, and the code is not a single-day event: it "
        "then counts as current whatever its date. Otherwise the entry counts by its last date",
    )
    onset_order: int | None = Field(
        description="Rank by first known date (onset or recorded), 1 = earliest; equal dates "
        "share a rank; null when undated"
    )
    references: list[ResourceRef] = Field(min_length=1)


class ProblemFamily(_Frozen):
    family: str = Field(description="Value set id of the family")
    title: str
    entries: list[ProblemEntry]


class EvidenceOutput(BaseModel):
    """Fields every evidence tool returns."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    patient_id: str
    as_of: date = Field(description="The date the record was read as of")
    is_diagnosis: Literal[False] = Field(
        default=False, description="Always false: these results are never a diagnosis"
    )
    notice: str = Field(description="Standard notice on how to read these results")
    data_completeness: list[DataCompleteness] = Field(
        description="Each data category read: available, empty, incomplete or failed. An "
        "empty record is not a clean record."
    )
    privacy: PrivacyNote = Field(
        description="What the sensitive-data policy withheld or restricted"
    )
    versions: Versions


class SafetyGateOutput(EvidenceOutput):
    safety_gate: SafetyGateResult
    gate_definition_version: str = Field(description="Version of the safety gate definition")


class ProblemListOutput(EvidenceOutput):
    families: list[ProblemFamily] = Field(
        description="Families with at least one coded condition, in a fixed order"
    )
    families_checked: list[str] = Field(description="Every family looked for")
    definition_version: str


class CutoffResult(_Frozen):
    """The cutoff for one score and whether it was applied."""

    id: str
    status: Literal[
        "applied", "not_applied_unverified", "not_applied_sex_unknown", "not_applied_no_score"
    ]
    met: bool | None = Field(description="Whether the score meets the cutoff; null if not applied")
    operator: str | None = Field(default=None, description="Only given once verified")
    value: float | None = Field(default=None, description="Only given once verified")
    sex: str | None = Field(default=None, description="any, male or female; once verified")
    source: str | None = Field(default=None, description="Where the verified cutoff comes from")


class ScreeningEntry(_Frozen):
    instrument: str | None = Field(description="Instrument id; null for an unknown instrument")
    instrument_title: str | None
    measure: Literal["total_score", "item", "risk_level", "unknown"]
    item: str | None = Field(default=None, description="Item number for an item score")
    date: date | None
    score: float | None
    answer: CodeRef | None = Field(default=None, description="A coded answer, e.g. a risk level")
    code: CodeRef | None = Field(description="The instrument code of this measure")
    code_verified: bool = Field(description="Whether that code is verified in the terminology")
    form: Literal["observation", "questionnaire_response"]
    questionnaire: str | None = Field(default=None, description="Questionnaire URL, if any")
    cutoff: CutoffResult | None = Field(description="Null when the measure has no cutoff")
    references: list[ResourceRef] = Field(min_length=1)


class ScreeningHistoryOutput(EvidenceOutput):
    entries: list[ScreeningEntry] = Field(description="Timeline, oldest first; undated last")
    instruments_checked: list[str]


class CareItem(_Frozen):
    """An ADHD referral, evaluation or care plan found in the record."""

    kind: Literal["service_request", "procedure", "care_plan"]
    status: str | None
    date: date | None
    excludes: bool = Field(description="Whether this item makes the patient already in care")
    why: str = Field(description="Why it does or does not exclude")
    references: list[ResourceRef] = Field(min_length=1)


class NarcolepsyFinding(_Frozen):
    """Reported separately; never an exclusion and never an ADHD signal."""

    condition_references: list[ResourceRef] = Field(min_length=1)
    medication_for_narcolepsy: bool = Field(
        description="A medication request or statement gives narcolepsy as its reason"
    )
    medication_references: list[ResourceRef]


class ExistingCareOutput(EvidenceOutput):
    excluded: bool | None = Field(
        description="True if already in ADHD care; false only if every check ran on complete "
        "data and found nothing; null otherwise (unknown)"
    )
    exclusions_checked: list[ExclusionCheck]
    care_items: list[CareItem]
    narcolepsy: NarcolepsyFinding | None
    definition_version: str


class IngredientRef(_Frozen):
    rxcui: str = Field(description="RxNorm ingredient code")
    name: str = Field(description="Ingredient name from the drug class data, not the record")


class ExposurePeriod(_Frozen):
    """A continuous period of exposure to one ingredient of a drug class."""

    drug_class: str = Field(description="Drug class id")
    ingredient: IngredientRef
    start: date
    end: date = Field(description="Last day covered, never after the as-of date")
    sources: list[Literal["dispense", "statement", "request"]] = Field(
        description="Record kinds the period is built from"
    )
    days_supply_assumed: bool = Field(
        description="True if any supply length was missing and the assumed length was used"
    )
    for_narcolepsy: bool = Field(
        description="A contributing order or statement gives narcolepsy as its reason"
    )
    references: list[ResourceRef] = Field(min_length=1)


class PrescriptionEntry(_Frozen):
    """One medication request in a drug class and whether it was dispensed."""

    drug_class: str
    ingredient: IngredientRef
    date: date | None
    fill_status: Literal["filled", "not_filled", "unknown"] = Field(
        description="unknown when the record has no dispensing data or it could not be read"
    )
    references: list[ResourceRef] = Field(min_length=1)


class AgentSummary(_Frozen):
    ingredient: IngredientRef
    first_date: date
    last_date: date = Field(description="Last day of exposure (or of the latest record)")
    references: list[ResourceRef] = Field(min_length=1)


class DistinctAgents(_Frozen):
    """Distinct ingredients of a class ever recorded; dose and brand variants collapse."""

    drug_class: str
    title: str
    count: int
    agents: list[AgentSummary]


class MedicationTimelineOutput(EvidenceOutput):
    exposures: list[ExposurePeriod] = Field(
        description="By class, then ingredient, then start date"
    )
    prescriptions: list[PrescriptionEntry]
    distinct_agents: list[DistinctAgents] = Field(description="One entry per class checked")
    unclassified_records: int = Field(
        description="Medication records in no class checked (not named, to keep output focused)"
    )
    classes_checked: list[str]
    definition_version: str
    drug_class_versions: list[str] = Field(description="'<class id> <version>' for each class")


class UtilizationEvent(_Frozen):
    kind: Literal["acute_care_visit", "injury_visit", "crash_as_driver", "psychiatric_stay"]
    date: dt.date | None = Field(description="Visit or admission date; null when undated")
    end: dt.date | None = Field(default=None, description="Discharge date of a stay, if known")
    follow_up: bool = Field(
        default=False,
        description="Injury visits only: true when every injury code on the visit is a "
        "subsequent-encounter or sequela code (seventh character other than A, B or C), so "
        "the visit is not a new injury and is not counted as one",
    )
    references: list[ResourceRef] = Field(
        min_length=1, description="The encounter first, then the conditions coding it"
    )


class WindowCount(_Frozen):
    measure: Literal[
        "acute_care_visit", "injury_visit", "crash_as_driver", "psychiatric_stay", "any_encounter"
    ]
    days_0_30: int
    days_31_180: int
    days_181_730: int
    total_730: int


class UtilizationOutput(EvidenceOutput):
    events: list[UtilizationEvent] = Field(
        description="Every event found, oldest first (undated last), by kind"
    )
    counts: list[WindowCount] = Field(
        description="Events per window before the as-of date. any_encounter is the overall "
        "record volume, so a rule can avoid simply rewarding frequent attendance"
    )
    visit_days_730: int = Field(description="Distinct days with any encounter in 730 days")
    missed_appointments: Literal["not_read"] = Field(
        description="Missed appointments are recorded in Appointment resources, which this "
        "server does not read yet"
    )
    psychiatric_stays_checked: bool = Field(
        description="False when the site maps no psychiatric encounter codes"
    )
    definition_version: str


class PsychosocialDomain(_Frozen):
    domain: str
    title: str
    status: Literal["found", "not_found", "unknown"] = Field(
        description="unknown when a category could not be read completely"
    )
    families: list[ProblemFamily] = Field(description="Coded findings grouped by value set")
    observation_references: list[ResourceRef] = Field(
        description="Social-history Observations whose coded value is in the domain"
    )


class MilitaryContext(_Frozen):
    separation_date: dt.date | None = Field(description="Null when unknown; never defaulted")
    status: Literal["recorded", "unknown"]
    reason: str | None = Field(default=None, description="Why the date is unknown")
    references: list[ResourceRef]


class PsychosocialOutput(EvidenceOutput):
    domains: list[PsychosocialDomain]
    military: MilitaryContext
    definition_version: str
