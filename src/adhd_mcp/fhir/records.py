"""Normalized, typed records produced from raw FHIR resources.

Records keep the resource reference and version for evidence linking. They deliberately
omit names, identifiers, addresses and free text: those are not needed by any rule.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from adhd_mcp.fhir.codes import Coding
from adhd_mcp.fhir.dates import DateRange
from adhd_mcp.models.domain import ResourceRef


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ref: ResourceRef


class Value(BaseModel):
    """A value from an observation, component or questionnaire answer.

    Free-text values are not kept; ``has_text`` records only that one was present. A value of
    a type not normalized here (Range, Ratio, Period, Time, ...) sets ``unsupported`` so it
    is never mistaken for a missing value.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    number: float | None = None
    comparator: str | None = None
    unit: str | None = None
    codings: tuple[Coding, ...] = ()
    boolean: bool | None = None
    date: DateRange | None = None
    has_text: bool = False
    unsupported: bool = False


class PatientRecord(_Record):
    administrative_gender: str | None
    birth_date: DateRange | None


class ConditionRecord(_Record):
    codes: tuple[Coding, ...]
    categories: tuple[Coding, ...]
    clinical_status: str | None
    verification_status: str | None
    onset: DateRange | None
    abatement: DateRange | None
    recorded: DateRange | None


class ObservationComponent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    codes: tuple[Coding, ...]
    value: Value | None


class ObservationRecord(_Record):
    status: str | None
    codes: tuple[Coding, ...]
    categories: tuple[Coding, ...]
    effective: DateRange | None
    value: Value | None
    components: tuple[ObservationComponent, ...]
    has_member: tuple[ResourceRef, ...]


class QuestionnaireItem(BaseModel):
    """One answered item. Nested groups are flattened; ``link_id`` identifies the item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    link_id: str
    answers: tuple[Value, ...]


class QuestionnaireResponseRecord(_Record):
    status: str | None
    questionnaire: str | None
    authored: DateRange | None
    items: tuple[QuestionnaireItem, ...]


class MedicationRecord(_Record):
    """A MedicationRequest, MedicationDispense or MedicationStatement (see ``ref``)."""

    status: str | None
    intent: str | None
    medication_codes: tuple[Coding, ...]
    medication_ref: ResourceRef | None
    date: DateRange | None
    days_supply: float | None
    quantity: float | None


class EncounterRecord(_Record):
    status: str | None
    encounter_class: Coding | None
    types: tuple[Coding, ...]
    service_type: tuple[Coding, ...]
    period: DateRange | None
    discharge_disposition: tuple[Coding, ...]
    reason_codes: tuple[Coding, ...]


class ProcedureRecord(_Record):
    status: str | None
    codes: tuple[Coding, ...]
    performed: DateRange | None


class ServiceRequestRecord(_Record):
    status: str | None
    intent: str | None
    codes: tuple[Coding, ...]
    categories: tuple[Coding, ...]
    authored: DateRange | None
    reason_codes: tuple[Coding, ...]


class CarePlanRecord(_Record):
    status: str | None
    intent: str | None
    categories: tuple[Coding, ...]
    period: DateRange | None


class FlagRecord(_Record):
    status: str | None
    codes: tuple[Coding, ...]
    categories: tuple[Coding, ...]
    period: DateRange | None


Record = (
    PatientRecord
    | ConditionRecord
    | ObservationRecord
    | QuestionnaireResponseRecord
    | MedicationRecord
    | EncounterRecord
    | ProcedureRecord
    | ServiceRequestRecord
    | CarePlanRecord
    | FlagRecord
)


class SkipReason(StrEnum):
    EXCLUDED_STATUS = "excluded_status"  # entered-in-error, or a refuted condition
    NO_ID = "no_id"
    MALFORMED = "malformed"
    UNSUPPORTED_TYPE = "unsupported_type"


class Skipped(BaseModel):
    """A resource that did not become a record, and why. Never silently dropped."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ref: ResourceRef | None
    resource_type: str | None
    reason: SkipReason
