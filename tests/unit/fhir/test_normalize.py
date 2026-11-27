"""Raw FHIR resources become typed records; unusable resources are reported, not hidden."""

from datetime import date
from typing import Any

import pytest

from adhd_mcp.fhir.codes import ICD10CM, LOINC, RXNORM, SNOMED, Coding
from adhd_mcp.fhir.dates import DatePrecision, DateRange
from adhd_mcp.fhir.normalize import normalize, normalize_many
from adhd_mcp.fhir.records import (
    ConditionRecord,
    EncounterRecord,
    FlagRecord,
    MedicationRecord,
    ObservationRecord,
    PatientRecord,
    QuestionnaireResponseRecord,
    ServiceRequestRecord,
    SkipReason,
    Value,
)
from adhd_mcp.models.domain import ResourceRef


def day(y: int, m: int, d: int) -> DateRange:
    return DateRange(start=date(y, m, d), end=date(y, m, d), precision=DatePrecision.DAY)


def condition(**extra: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "resourceType": "Condition",
        "id": "syn-c1",
        "meta": {"versionId": "3"},
        "code": {
            "coding": [
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "F15.10"},
                {"system": "http://snomed.info/sct", "code": "191939002"},
            ]
        },
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "verificationStatus": {"coding": [{"code": "confirmed"}]},
        "onsetDateTime": "2023-05",
        "recordedDate": "2023-06-01T09:00:00Z",
    }
    raw.update(extra)
    return raw


def test_condition_is_normalized_with_reference_and_version() -> None:
    record = normalize(condition())
    assert isinstance(record, ConditionRecord)
    assert record.ref == ResourceRef(resource_type="Condition", id="syn-c1", version="3")
    assert record.codes == (
        Coding(system=ICD10CM, code="F15.10"),
        Coding(system=SNOMED, code="191939002"),
    )
    assert record.clinical_status == "active"
    assert record.verification_status == "confirmed"
    assert record.onset == DateRange(
        start=date(2023, 5, 1), end=date(2023, 5, 31), precision=DatePrecision.MONTH
    )
    assert record.recorded == day(2023, 6, 1)


@pytest.mark.parametrize("status", ["entered-in-error", "refuted"])
def test_entered_in_error_and_refuted_conditions_are_dropped(status: str) -> None:
    result = normalize_many([condition(verificationStatus={"coding": [{"code": status}]})])
    assert result.records == ()
    assert result.skipped[0].reason is SkipReason.EXCLUDED_STATUS
    assert result.skipped[0].ref == ResourceRef(resource_type="Condition", id="syn-c1", version="3")


def test_entered_in_error_observation_is_dropped() -> None:
    raw = {"resourceType": "Observation", "id": "o1", "status": "entered-in-error", "code": {}}
    assert normalize(raw) is None


def test_missing_optional_fields_are_tolerated() -> None:
    record = normalize({"resourceType": "Condition", "id": "c-bare"})
    assert isinstance(record, ConditionRecord)
    assert record.codes == ()
    assert record.onset is None
    assert record.clinical_status is None
    assert record.ref.version is None


def test_onset_period_and_abatement() -> None:
    record = normalize(
        condition(
            onsetDateTime=None,
            onsetPeriod={"start": "2020-01-01"},
            abatementDateTime="2021-02-03",
        )
    )
    assert isinstance(record, ConditionRecord)
    assert record.onset is not None
    assert record.onset.start == date(2020, 1, 1)
    assert record.abatement == day(2021, 2, 3)


def test_resource_without_id_is_skipped() -> None:
    result = normalize_many([{"resourceType": "Condition"}])
    assert result.records == ()
    assert result.skipped[0].reason is SkipReason.NO_ID
    assert result.skipped[0].ref is None


def test_malformed_date_is_skipped_not_guessed() -> None:
    result = normalize_many([condition(onsetDateTime="sometime in May")])
    assert result.records == ()
    assert result.skipped[0].reason is SkipReason.MALFORMED


def test_unsupported_resource_type_is_skipped() -> None:
    result = normalize_many([{"resourceType": "DocumentReference", "id": "d1"}])
    assert result.skipped[0].reason is SkipReason.UNSUPPORTED_TYPE


def test_patient_keeps_no_names_or_identifiers() -> None:
    record = normalize(
        {
            "resourceType": "Patient",
            "id": "p1",
            "gender": "female",
            "birthDate": "1985-07",
            "name": [{"family": "Synthetic"}],
            "identifier": [{"value": "SYN-1"}],
        }
    )
    assert isinstance(record, PatientRecord)
    assert record.administrative_gender == "female"
    assert record.birth_date is not None
    assert record.birth_date.start == date(1985, 7, 1)
    assert "name" not in PatientRecord.model_fields
    assert "identifier" not in PatientRecord.model_fields


def test_observation_panel_with_members_and_components() -> None:
    record = normalize(
        {
            "resourceType": "Observation",
            "id": "o-panel",
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "44249-1"}]},
            "effectiveDateTime": "2025-01-02T10:00:00Z",
            "hasMember": [{"reference": "Observation/o-item9"}],
            "component": [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "44260-8"}]},
                    "valueInteger": 1,
                }
            ],
            "valueQuantity": {"value": 7, "unit": "{score}"},
        }
    )
    assert isinstance(record, ObservationRecord)
    assert record.effective == day(2025, 1, 2)
    assert record.value == Value(number=7.0, unit="{score}")
    assert record.has_member == (ResourceRef(resource_type="Observation", id="o-item9"),)
    assert record.components[0].codes == (Coding(system=LOINC, code="44260-8"),)
    assert record.components[0].value == Value(number=1.0)


def test_observation_coded_value_and_period() -> None:
    record = normalize(
        {
            "resourceType": "Observation",
            "id": "o2",
            "status": "final",
            "code": {},
            "effectivePeriod": {"start": "2025-01-01", "end": "2025-01-03"},
            "valueCodeableConcept": {"coding": [{"system": "http://loinc.org", "code": "LA1"}]},
        }
    )
    assert isinstance(record, ObservationRecord)
    assert record.value == Value(codings=(Coding(system=LOINC, code="LA1"),))
    assert record.effective is not None
    assert record.effective.precision is DatePrecision.PERIOD


def test_observation_string_value_is_not_kept_as_text() -> None:
    record = normalize(
        {"resourceType": "Observation", "id": "o3", "status": "final", "valueString": "note"}
    )
    assert isinstance(record, ObservationRecord)
    assert record.value == Value(has_text=True)


def test_questionnaire_response_items_are_flattened() -> None:
    record = normalize(
        {
            "resourceType": "QuestionnaireResponse",
            "id": "qr1",
            "status": "completed",
            "questionnaire": "http://example.org/Questionnaire/phq-9",
            "authored": "2025-02-03",
            "item": [
                {
                    "linkId": "group",
                    "item": [
                        {"linkId": "9", "answer": [{"valueInteger": 2}]},
                        {
                            "linkId": "10",
                            "answer": [
                                {"valueCoding": {"system": "http://loinc.org", "code": "LA"}}
                            ],
                        },
                    ],
                },
                {"linkId": "total", "answer": [{"valueDecimal": 12.0}]},
            ],
        }
    )
    assert isinstance(record, QuestionnaireResponseRecord)
    assert record.questionnaire == "http://example.org/Questionnaire/phq-9"
    assert record.authored == day(2025, 2, 3)
    assert [(i.link_id, i.answers) for i in record.items] == [
        ("9", (Value(number=2.0),)),
        ("10", (Value(codings=(Coding(system=LOINC, code="LA"),)),)),
        ("total", (Value(number=12.0),)),
    ]


def test_medication_request_with_codeable_concept_and_supply() -> None:
    record = normalize(
        {
            "resourceType": "MedicationRequest",
            "id": "mr1",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "123"}]
            },
            "authoredOn": "2024-04-05",
            "dispenseRequest": {
                "expectedSupplyDuration": {"value": 30, "unit": "days", "code": "d"},
                "quantity": {"value": 60},
            },
        }
    )
    assert isinstance(record, MedicationRecord)
    assert record.ref.resource_type == "MedicationRequest"
    assert record.intent == "order"
    assert record.medication_codes == (Coding(system=RXNORM, code="123"),)
    assert record.date == day(2024, 4, 5)
    assert record.days_supply == 30.0
    assert record.quantity == 60.0


def test_medication_reference_is_resolved_from_included_medication() -> None:
    medication = {
        "resourceType": "Medication",
        "id": "med1",
        "code": {
            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "9"}]
        },
    }
    dispense = {
        "resourceType": "MedicationDispense",
        "id": "md1",
        "status": "completed",
        "medicationReference": {"reference": "Medication/med1"},
        "whenHandedOver": "2024-04-06",
        "daysSupply": {"value": 28},
    }
    result = normalize_many([dispense, medication])
    (record,) = result.records
    assert isinstance(record, MedicationRecord)
    assert record.medication_ref == ResourceRef(resource_type="Medication", id="med1")
    assert record.medication_codes == (Coding(system=RXNORM, code="9"),)
    assert record.days_supply == 28.0


def test_contained_medication_is_resolved() -> None:
    statement = {
        "resourceType": "MedicationStatement",
        "id": "ms1",
        "status": "active",
        "contained": [
            {
                "resourceType": "Medication",
                "id": "m",
                "code": {"coding": [{"system": "urn:oid:2.16.840.1.113883.6.88", "code": "7"}]},
            }
        ],
        "medicationReference": {"reference": "#m"},
        "effectivePeriod": {"start": "2024-01-01"},
    }
    record = normalize(statement)
    assert isinstance(record, MedicationRecord)
    assert record.medication_codes == (Coding(system=RXNORM, code="7"),)
    assert record.medication_ref is None


def test_encounter_fields() -> None:
    record = normalize(
        {
            "resourceType": "Encounter",
            "id": "e1",
            "status": "finished",
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "IMP",
            },
            "type": [{"coding": [{"system": "http://snomed.info/sct", "code": "32485007"}]}],
            "serviceType": {"coding": [{"system": "http://example.org/svc", "code": "psych"}]},
            "period": {"start": "2025-01-01", "end": "2025-01-09"},
            "hospitalization": {
                "dischargeDisposition": {"coding": [{"system": "http://x", "code": "home"}]}
            },
            "reasonCode": [
                {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "r45.851"}]}
            ],
        }
    )
    assert isinstance(record, EncounterRecord)
    assert record.encounter_class == Coding(
        system="http://terminology.hl7.org/CodeSystem/v3-ActCode", code="IMP"
    )
    assert record.types == (Coding(system=SNOMED, code="32485007"),)
    assert record.service_type == (Coding(system="http://example.org/svc", code="psych"),)
    assert record.period is not None
    assert record.period.end == date(2025, 1, 9)
    assert record.discharge_disposition == (Coding(system="http://x", code="home"),)
    assert record.reason_codes == (Coding(system=ICD10CM, code="R45.851"),)


def test_service_request_and_flag() -> None:
    sr = normalize(
        {
            "resourceType": "ServiceRequest",
            "id": "sr1",
            "status": "revoked",
            "intent": "order",
            "authoredOn": "2022",
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "1"}]},
        }
    )
    assert isinstance(sr, ServiceRequestRecord)
    assert sr.status == "revoked"
    assert sr.authored is not None
    flag = normalize(
        {"resourceType": "Flag", "id": "f1", "status": "active", "period": {"start": "2025"}}
    )
    assert isinstance(flag, FlagRecord)
    assert flag.period is not None


def test_quantity_comparator_is_kept() -> None:
    record = normalize(
        {
            "resourceType": "Observation",
            "id": "o4",
            "status": "final",
            "valueQuantity": {"value": 20, "comparator": "<", "unit": "mg/dL"},
        }
    )
    assert isinstance(record, ObservationRecord)
    assert record.value == Value(number=20.0, comparator="<", unit="mg/dL")


@pytest.mark.parametrize(
    "element",
    [
        {"valueRange": {"low": {"value": 1}}},
        {"valueRatio": {"numerator": {"value": 1}}},
        {"valuePeriod": {"start": "2024"}},
        {"valueTime": "10:00:00"},
    ],
)
def test_unsupported_value_types_are_flagged_not_lost(element: dict[str, Any]) -> None:
    record = normalize({"resourceType": "Observation", "id": "o5", "status": "final", **element})
    assert isinstance(record, ObservationRecord)
    assert record.value == Value(unsupported=True)


@pytest.mark.parametrize("kind", ["MedicationRequest", "MedicationStatement"])
def test_medication_reason_codes_are_kept(kind: str) -> None:
    record = normalize(
        {
            "resourceType": kind,
            "id": "m1",
            "status": "active",
            "medicationCodeableConcept": {"coding": [{"system": RXNORM, "code": "725"}]},
            "reasonCode": [{"coding": [{"system": ICD10CM, "code": "G47.419"}], "text": "x"}],
            "subject": {"reference": "Patient/p"},
        }
    )
    assert isinstance(record, MedicationRecord)
    assert record.reason_codes == (Coding(system=ICD10CM, code="G47.419"),)
