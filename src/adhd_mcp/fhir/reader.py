"""Typed, normalized access to one patient's data through any ``FhirReadPort``.

The rest of the system asks for "this patient's conditions" or "observations in this value
set since this date" and gets normalized records plus a list of anything skipped, without
knowing where the data came from.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict

from adhd_mcp.fhir.codes import Coding
from adhd_mcp.fhir.errors import FhirRequestError
from adhd_mcp.fhir.normalize import normalize, normalize_many
from adhd_mcp.fhir.port import FhirReadPort, SearchType, SearchWarning
from adhd_mcp.fhir.records import (
    CarePlanRecord,
    ConditionRecord,
    EncounterRecord,
    FlagRecord,
    MedicationRecord,
    ObservationRecord,
    PatientRecord,
    ProcedureRecord,
    QuestionnaireResponseRecord,
    Record,
    ServiceRequestRecord,
    Skipped,
    SkipReason,
)
from adhd_mcp.fhir.search import Codes, matches_filters
from adhd_mcp.terminology import ValueSet
from adhd_mcp.terminology.value_sets import covered_systems


class ReadResult[R: BaseModel](BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    records: tuple[R, ...]
    skipped: tuple[Skipped, ...]
    warnings: tuple[SearchWarning, ...] = ()


def merge_reads[R: BaseModel](*reads: ReadResult[R]) -> ReadResult[R]:
    """Several reads of one type as one: records once each (by reference), every skip and
    warning kept."""
    seen: set[tuple[str, str]] = set()
    records: list[R] = []
    for read in reads:
        for record in read.records:
            ref = record.ref  # type: ignore[attr-defined]
            if (ref.resource_type, ref.id) not in seen:
                seen.add((ref.resource_type, ref.id))
                records.append(record)
    return ReadResult[R](
        records=tuple(records),
        skipped=tuple(s for r in reads for s in r.skipped),
        warnings=tuple(w for r in reads for w in r.warnings),
    )


def record_codes(record: Record) -> tuple[Coding, ...]:  # noqa: PLR0911
    """Every coding a value set filter considers for a record."""
    match record:
        case MedicationRecord():
            return record.medication_codes
        case EncounterRecord():
            return record.types + record.service_type + record.reason_codes
        case ObservationRecord():
            return record.codes + tuple(c for comp in record.components for c in comp.codes)
        case ServiceRequestRecord():
            return record.codes + record.reason_codes
        case ConditionRecord() | ProcedureRecord() | FlagRecord():
            return record.codes
        case CarePlanRecord():
            return record.categories
        case _:
            return ()


def _unrecognized(record: Record) -> bool:
    """A Condition with no coding in a system the value sets cover: nothing can match it, so
    it is reported as skipped rather than read as a record that matched nothing."""
    return isinstance(record, ConditionRecord) and not any(
        c.system in covered_systems() for c in record.codes
    )


class PatientRecords:
    def __init__(self, port: FhirReadPort) -> None:
        self._port = port

    async def patient(self, patient_id: str) -> PatientRecord:
        record = normalize(await self._port.read_patient(patient_id))
        if not isinstance(record, PatientRecord):
            raise FhirRequestError(
                "read Patient: resource could not be normalized", transient=False
            )
        return record

    async def _read[R: BaseModel](
        self,
        resource_type: SearchType,
        record_type: type[R],
        patient_id: str,
        since: date | None,
        value_set: ValueSet | None,
        *,
        categories: tuple[str, ...] = (),
        codes: Codes = (),
    ) -> ReadResult[R]:
        found = await self._port.search(
            resource_type, patient_id, since=since, categories=categories, codes=codes
        )
        # The filters again, locally: a server that ignores them must not widen the read.
        normalized = normalize_many(
            r for r in found.resources if matches_filters(r, categories, codes)
        )
        unrecognized = tuple(
            Skipped(
                ref=r.ref, resource_type=r.ref.resource_type, reason=SkipReason.UNRECOGNIZED_CODING
            )
            for r in normalized.records
            if _unrecognized(r)
        )
        records = tuple(
            r
            for r in normalized.records
            if isinstance(r, record_type)
            and not _unrecognized(r)
            and (value_set is None or value_set.matching_codings(record_codes(r)))
        )
        return ReadResult[R](
            records=records, skipped=normalized.skipped + unrecognized, warnings=found.warnings
        )

    async def conditions(
        self, patient_id: str, *, since: date | None = None, value_set: ValueSet | None = None
    ) -> ReadResult[ConditionRecord]:
        return await self._read("Condition", ConditionRecord, patient_id, since, value_set)

    async def observations(
        self,
        patient_id: str,
        *,
        since: date | None = None,
        value_set: ValueSet | None = None,
        categories: tuple[str, ...] = (),
        codes: Codes = (),
    ) -> ReadResult[ObservationRecord]:
        """Observations, restricted to ``categories`` or ``codes`` when given (peer review
        01, D1: laboratory results and vital signs are never needed)."""
        return await self._read(
            "Observation",
            ObservationRecord,
            patient_id,
            since,
            value_set,
            categories=categories,
            codes=codes,
        )

    async def questionnaire_responses(
        self, patient_id: str, *, since: date | None = None
    ) -> ReadResult[QuestionnaireResponseRecord]:
        return await self._read(
            "QuestionnaireResponse", QuestionnaireResponseRecord, patient_id, since, None
        )

    async def medication_requests(
        self, patient_id: str, *, since: date | None = None, value_set: ValueSet | None = None
    ) -> ReadResult[MedicationRecord]:
        return await self._read("MedicationRequest", MedicationRecord, patient_id, since, value_set)

    async def medication_dispenses(
        self, patient_id: str, *, since: date | None = None, value_set: ValueSet | None = None
    ) -> ReadResult[MedicationRecord]:
        return await self._read(
            "MedicationDispense", MedicationRecord, patient_id, since, value_set
        )

    async def medication_statements(
        self, patient_id: str, *, since: date | None = None, value_set: ValueSet | None = None
    ) -> ReadResult[MedicationRecord]:
        return await self._read(
            "MedicationStatement", MedicationRecord, patient_id, since, value_set
        )

    async def encounters(
        self, patient_id: str, *, since: date | None = None, value_set: ValueSet | None = None
    ) -> ReadResult[EncounterRecord]:
        return await self._read("Encounter", EncounterRecord, patient_id, since, value_set)

    async def procedures(
        self, patient_id: str, *, since: date | None = None, value_set: ValueSet | None = None
    ) -> ReadResult[ProcedureRecord]:
        return await self._read("Procedure", ProcedureRecord, patient_id, since, value_set)

    async def service_requests(
        self, patient_id: str, *, since: date | None = None, value_set: ValueSet | None = None
    ) -> ReadResult[ServiceRequestRecord]:
        return await self._read(
            "ServiceRequest", ServiceRequestRecord, patient_id, since, value_set
        )

    async def care_plans(
        self, patient_id: str, *, since: date | None = None, value_set: ValueSet | None = None
    ) -> ReadResult[CarePlanRecord]:
        return await self._read("CarePlan", CarePlanRecord, patient_id, since, value_set)

    async def flags(
        self, patient_id: str, *, since: date | None = None, value_set: ValueSet | None = None
    ) -> ReadResult[FlagRecord]:
        return await self._read("Flag", FlagRecord, patient_id, since, value_set)
