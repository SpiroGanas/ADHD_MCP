"""Convert raw FHIR R4 resources to normalized records.

Rules applied to every resource:

* ``entered-in-error`` resources are excluded, and so are refuted conditions.
* A resource without an id cannot be cited, so it is skipped.
* A malformed value (for example an unparseable date) skips the resource rather than
  guessing. Every skip is reported in :class:`Normalized`, never silently dropped.
* Free text is not copied into records.
"""

from collections.abc import Callable, Iterable, Mapping
from typing import Any, get_args

from pydantic import BaseModel, ConfigDict, ValidationError

from adhd_mcp.fhir.codes import Coding, normalize_coding, normalize_concept
from adhd_mcp.fhir.dates import DateRange, parse_fhir_date, parse_period
from adhd_mcp.fhir.records import (
    CarePlanRecord,
    ConditionRecord,
    EncounterRecord,
    FlagRecord,
    MedicationRecord,
    ObservationComponent,
    ObservationRecord,
    PatientRecord,
    ProcedureRecord,
    QuestionnaireItem,
    QuestionnaireResponseRecord,
    Record,
    ServiceRequestRecord,
    Skipped,
    SkipReason,
    Value,
)
from adhd_mcp.models.domain import ResourceRef, ResourceType

Raw = Mapping[str, Any]

_RESOURCE_TYPES: frozenset[str] = frozenset(get_args(ResourceType))
_EXCLUDED_STATUSES = frozenset({"entered-in-error"})
_EXCLUDED_VERIFICATION = frozenset({"entered-in-error", "refuted"})


class Normalized(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    records: tuple[Record, ...]
    skipped: tuple[Skipped, ...]


class _ExcludedError(Exception):
    pass


def _ref(raw: Raw) -> ResourceRef:
    meta = raw.get("meta") or {}
    return ResourceRef(
        resource_type=raw["resourceType"], id=raw["id"], version=meta.get("versionId")
    )


def parse_reference(reference: str | None) -> ResourceRef | None:
    """Parse a relative ``Type/id`` reference, or an absolute http(s) one ending in
    ``Type/id`` or ``Type/id/_history/version`` (VA Lighthouse writes every reference
    absolute); ``None`` for anything else (contained, ``urn:``, unknown types). Only the id
    is kept: references are resolved within one patient's search results."""
    if not reference:
        return None
    parts = reference.split("/")
    if reference.startswith(("https://", "http://")):
        if len(parts) >= 6 and parts[-2] == "_history":
            parts = parts[:-2]
        parts = parts[-2:]
    if len(parts) != 2 or parts[0] not in _RESOURCE_TYPES or not parts[1]:
        return None
    return ResourceRef(resource_type=parts[0], id=parts[1])


def _status_code(concept: Raw | None) -> str | None:
    codings = normalize_concept(concept)
    return codings[0].code if codings else None


def _date(raw: Raw, key: str) -> DateRange | None:
    value = raw.get(key)
    return parse_fhir_date(value) if value else None


def _choice_date(raw: Raw, prefix: str) -> DateRange | None:
    """A ``[x]`` element that may be a dateTime/date/instant or a Period."""
    for suffix in ("DateTime", "Date", "Instant"):
        if raw.get(prefix + suffix):
            return parse_fhir_date(raw[prefix + suffix])
    period = raw.get(prefix + "Period")
    return parse_period(period) if period else None


def _concepts(raw: Iterable[Raw] | None) -> tuple[Coding, ...]:
    return tuple(c for concept in raw or [] for c in normalize_concept(concept))


def _value(raw: Raw, prefix: str = "value") -> Value | None:  # noqa: PLR0911
    if (q := raw.get(prefix + "Quantity")) is not None:
        number = q.get("value")
        return Value(
            number=float(number) if number is not None else None,
            comparator=q.get("comparator"),
            unit=q.get("unit"),
        )
    for suffix in ("Integer", "Decimal"):
        if (n := raw.get(prefix + suffix)) is not None:
            return Value(number=float(n))
    if (c := raw.get(prefix + "CodeableConcept")) is not None:
        return Value(codings=normalize_concept(c))
    if (c := raw.get(prefix + "Coding")) is not None:
        coding = normalize_coding(c)
        return Value(codings=(coding,) if coding else ())
    if (b := raw.get(prefix + "Boolean")) is not None:
        return Value(boolean=bool(b))
    for suffix in ("DateTime", "Date"):
        if raw.get(prefix + suffix):
            return Value(date=parse_fhir_date(raw[prefix + suffix]))
    if raw.get(prefix + "String") is not None:
        return Value(has_text=True)
    if any(key.startswith(prefix) and key != prefix for key in raw):
        return Value(unsupported=True)
    return None


def _check_status(raw: Raw) -> None:
    if raw.get("status") in _EXCLUDED_STATUSES:
        raise _ExcludedError


def _patient(raw: Raw) -> PatientRecord:
    deceased_date = _date(raw, "deceasedDateTime")
    flag = raw.get("deceasedBoolean")
    deceased = True if deceased_date is not None else (bool(flag) if flag is not None else None)
    return PatientRecord(
        ref=_ref(raw),
        administrative_gender=raw.get("gender"),
        birth_date=_date(raw, "birthDate"),
        deceased=deceased,
        deceased_date=deceased_date,
    )


def _condition(raw: Raw) -> ConditionRecord:
    verification = _status_code(raw.get("verificationStatus"))
    if verification in _EXCLUDED_VERIFICATION:
        raise _ExcludedError
    return ConditionRecord(
        ref=_ref(raw),
        codes=normalize_concept(raw.get("code")),
        categories=_concepts(raw.get("category")),
        clinical_status=_status_code(raw.get("clinicalStatus")),
        verification_status=verification,
        onset=_choice_date(raw, "onset"),
        abatement=_choice_date(raw, "abatement"),
        recorded=_date(raw, "recordedDate"),
        encounter=parse_reference((raw.get("encounter") or {}).get("reference")),
    )


def _observation(raw: Raw) -> ObservationRecord:
    _check_status(raw)
    return ObservationRecord(
        ref=_ref(raw),
        status=raw.get("status"),
        codes=normalize_concept(raw.get("code")),
        categories=_concepts(raw.get("category")),
        effective=_choice_date(raw, "effective"),
        value=_value(raw),
        components=tuple(
            ObservationComponent(codes=normalize_concept(c.get("code")), value=_value(c))
            for c in raw.get("component") or []
        ),
        has_member=tuple(
            ref for m in raw.get("hasMember") or [] if (ref := parse_reference(m.get("reference")))
        ),
    )


def _flatten_items(items: Iterable[Raw]) -> list[QuestionnaireItem]:
    flat: list[QuestionnaireItem] = []
    for item in items:
        answers = item.get("answer") or []
        if answers:
            flat.append(
                QuestionnaireItem(
                    link_id=item["linkId"],
                    answers=tuple(v for a in answers if (v := _value(a)) is not None),
                )
            )
        flat.extend(_flatten_items(item.get("item") or []))
        for answer in answers:
            flat.extend(_flatten_items(answer.get("item") or []))
    return flat


def _questionnaire_response(raw: Raw) -> QuestionnaireResponseRecord:
    _check_status(raw)
    return QuestionnaireResponseRecord(
        ref=_ref(raw),
        status=raw.get("status"),
        questionnaire=raw.get("questionnaire"),
        authored=_date(raw, "authored"),
        items=tuple(_flatten_items(raw.get("item") or [])),
    )


def _medication(raw: Raw, medications: Mapping[str, Raw]) -> MedicationRecord:
    _check_status(raw)
    codes = normalize_concept(raw.get("medicationCodeableConcept"))
    medication_ref: ResourceRef | None = None
    reference = (raw.get("medicationReference") or {}).get("reference")
    if reference and reference.startswith("#"):
        contained = {c.get("id"): c for c in raw.get("contained") or []}
        codes = normalize_concept((contained.get(reference[1:]) or {}).get("code"))
    elif reference:
        medication_ref = parse_reference(reference)
        if medication_ref is not None and medication_ref.id in medications:
            codes = normalize_concept(medications[medication_ref.id].get("code"))

    kind = raw["resourceType"]
    links = raw.get("authorizingPrescription") or raw.get("basedOn") or []
    prescriptions = tuple(
        ref
        for link in links
        if (ref := parse_reference(link.get("reference"))) is not None
        and ref.resource_type == "MedicationRequest"
    )
    days_supply: float | None = None
    quantity: float | None = None
    if kind == "MedicationRequest":
        when = _date(raw, "authoredOn")
        dispense_request = raw.get("dispenseRequest") or {}
        duration = dispense_request.get("expectedSupplyDuration") or {}
        if duration.get("value") is not None and duration.get("code", "d") == "d":
            days_supply = float(duration["value"])
        if (dispense_request.get("quantity") or {}).get("value") is not None:
            quantity = float(dispense_request["quantity"]["value"])
    elif kind == "MedicationDispense":
        when = _date(raw, "whenHandedOver")
        if (raw.get("daysSupply") or {}).get("value") is not None:
            days_supply = float(raw["daysSupply"]["value"])
        if (raw.get("quantity") or {}).get("value") is not None:
            quantity = float(raw["quantity"]["value"])
    else:
        when = _choice_date(raw, "effective")
    return MedicationRecord(
        ref=_ref(raw),
        status=raw.get("status"),
        intent=raw.get("intent"),
        medication_codes=codes,
        medication_ref=medication_ref,
        date=when,
        days_supply=days_supply,
        quantity=quantity,
        reason_codes=_concepts(raw.get("reasonCode")),
        prescriptions=prescriptions,
    )


def _encounter(raw: Raw) -> EncounterRecord:
    _check_status(raw)
    encounter_class = raw.get("class")
    return EncounterRecord(
        ref=_ref(raw),
        status=raw.get("status"),
        encounter_class=normalize_coding(encounter_class) if encounter_class else None,
        types=_concepts(raw.get("type")),
        service_type=normalize_concept(raw.get("serviceType")),
        period=parse_period(raw["period"]) if raw.get("period") else None,
        discharge_disposition=normalize_concept(
            (raw.get("hospitalization") or {}).get("dischargeDisposition")
        ),
        reason_codes=_concepts(raw.get("reasonCode")),
        diagnoses=tuple(
            ref
            for d in raw.get("diagnosis") or []
            if (ref := parse_reference((d.get("condition") or {}).get("reference")))
            and ref.resource_type == "Condition"
        ),
    )


def _procedure(raw: Raw) -> ProcedureRecord:
    _check_status(raw)
    return ProcedureRecord(
        ref=_ref(raw),
        status=raw.get("status"),
        codes=normalize_concept(raw.get("code")),
        performed=_choice_date(raw, "performed"),
    )


def _service_request(raw: Raw) -> ServiceRequestRecord:
    _check_status(raw)
    return ServiceRequestRecord(
        ref=_ref(raw),
        status=raw.get("status"),
        intent=raw.get("intent"),
        codes=normalize_concept(raw.get("code")),
        categories=_concepts(raw.get("category")),
        authored=_date(raw, "authoredOn"),
        reason_codes=_concepts(raw.get("reasonCode")),
    )


def _care_plan(raw: Raw) -> CarePlanRecord:
    _check_status(raw)
    return CarePlanRecord(
        ref=_ref(raw),
        status=raw.get("status"),
        intent=raw.get("intent"),
        categories=_concepts(raw.get("category")),
        period=parse_period(raw["period"]) if raw.get("period") else None,
    )


def _flag(raw: Raw) -> FlagRecord:
    _check_status(raw)
    return FlagRecord(
        ref=_ref(raw),
        status=raw.get("status"),
        codes=normalize_concept(raw.get("code")),
        categories=_concepts(raw.get("category")),
        period=parse_period(raw["period"]) if raw.get("period") else None,
    )


_SIMPLE: dict[str, Callable[[Raw], Record]] = {
    "Patient": _patient,
    "Condition": _condition,
    "Observation": _observation,
    "QuestionnaireResponse": _questionnaire_response,
    "Encounter": _encounter,
    "Procedure": _procedure,
    "ServiceRequest": _service_request,
    "CarePlan": _care_plan,
    "Flag": _flag,
}
_MEDICATION_TYPES = frozenset({"MedicationRequest", "MedicationDispense", "MedicationStatement"})


def _one(raw: Raw, medications: Mapping[str, Raw]) -> Record | Skipped:
    resource_type = raw.get("resourceType")
    if resource_type not in _SIMPLE and resource_type not in _MEDICATION_TYPES:
        return Skipped(ref=None, resource_type=resource_type, reason=SkipReason.UNSUPPORTED_TYPE)
    if not raw.get("id"):
        return Skipped(ref=None, resource_type=resource_type, reason=SkipReason.NO_ID)
    try:
        if resource_type in _MEDICATION_TYPES:
            return _medication(raw, medications)
        return _SIMPLE[resource_type](raw)
    except _ExcludedError:
        reason = SkipReason.EXCLUDED_STATUS
    except (ValueError, TypeError, KeyError, AttributeError, ValidationError):
        reason = SkipReason.MALFORMED
    return Skipped(ref=_ref(raw), resource_type=resource_type, reason=reason)


def normalize_many(resources: Iterable[Raw]) -> Normalized:
    """Normalize a batch. Medication resources in the batch resolve medication references
    and are not returned as records themselves."""
    batch = list(resources)
    medications = {
        r["id"]: r for r in batch if r.get("resourceType") == "Medication" and r.get("id")
    }
    records: list[Record] = []
    skipped: list[Skipped] = []
    for raw in batch:
        if raw.get("resourceType") == "Medication":
            continue
        result = _one(raw, medications)
        (skipped if isinstance(result, Skipped) else records).append(result)  # type: ignore[arg-type]
    return Normalized(records=tuple(records), skipped=tuple(skipped))


def normalize(raw: Raw) -> Record | None:
    """Normalize one resource; ``None`` if it was skipped."""
    result = _one(raw, {})
    return None if isinstance(result, Skipped) else result
