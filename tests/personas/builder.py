"""Small helpers for hand-building synthetic FHIR R4 resources.

Every persona is built here and written to ``bundles/`` by ``scripts/build_personas.py``.
A test checks the committed JSON matches this builder, so edit the definitions, not the JSON.
"""

from typing import Any

ICD10CM = "http://hl7.org/fhir/sid/icd-10-cm"
SNOMED = "http://snomed.info/sct"
LOINC = "http://loinc.org"
RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
ACT_CODE = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
SYNTHETIC_LOCAL = "urn:adhd-mcp:synthetic-local-code"
SYNTHETIC_ID = "urn:adhd-mcp:synthetic-id"
HTEST = {"system": "http://terminology.hl7.org/CodeSystem/v3-ActReason", "code": "HTEST"}

Resource = dict[str, Any]


def coding(system: str, code: str, display: str | None = None) -> dict[str, str]:
    out = {"system": system, "code": code}
    if display:
        out["display"] = display
    return out


def concept(*codings: dict[str, str]) -> dict[str, Any]:
    return {"coding": list(codings)}


class PersonaBuilder:
    """Builds one persona's resources with globally unique, obviously synthetic ids."""

    def __init__(
        self, key: str, *, gender: str, birth_date: str, number: int | None = None
    ) -> None:
        self.key = key
        self.patient_id = f"{key}-patient"
        self.resources: list[Resource] = []
        self._counters: dict[str, int] = {}
        number = int(key[1:]) if number is None else number
        self.resources.append(
            {
                "resourceType": "Patient",
                "id": self.patient_id,
                "meta": {"tag": [HTEST]},
                "identifier": [{"system": SYNTHETIC_ID, "value": f"SYN-{number:04d}"}],
                "name": [{"family": "Synthetic", "given": [f"Persona{number:02d}"]}],
                "gender": gender,
                "birthDate": birth_date,
            }
        )

    def _id(self, short: str) -> str:
        self._counters[short] = self._counters.get(short, 0) + 1
        return f"{self.key}-{short}-{self._counters[short]}"

    def _add(self, resource: Resource) -> str:
        self.resources.append(resource)
        return str(resource["id"])

    @property
    def subject(self) -> dict[str, str]:
        return {"reference": f"Patient/{self.patient_id}"}

    def condition(
        self,
        code: str,
        display: str,
        *,
        onset: str | None = None,
        recorded: str | None = None,
        clinical: str = "active",
        verification: str = "confirmed",
        category: str = "problem-list-item",
        encounter: str | None = None,
        extra_codings: tuple[dict[str, str], ...] = (),
    ) -> str:
        resource: Resource = {
            "resourceType": "Condition",
            "id": self._id("cond"),
            "clinicalStatus": concept(
                coding("http://terminology.hl7.org/CodeSystem/condition-clinical", clinical)
            ),
            "verificationStatus": concept(
                coding("http://terminology.hl7.org/CodeSystem/condition-ver-status", verification)
            ),
            "category": [
                concept(
                    coding("http://terminology.hl7.org/CodeSystem/condition-category", category)
                )
            ],
            "code": concept(coding(ICD10CM, code, display), *extra_codings),
            "subject": self.subject,
        }
        if encounter:
            resource["encounter"] = {"reference": f"Encounter/{encounter}"}
        if onset:
            resource["onsetDateTime"] = onset
        if recorded:
            resource["recordedDate"] = recorded
        return self._add(resource)

    def encounter(
        self,
        class_code: str,
        start: str,
        end: str | None = None,
        *,
        service: str | None = None,
        reasons: tuple[tuple[str, str], ...] = (),
        status: str = "finished",
    ) -> str:
        resource: Resource = {
            "resourceType": "Encounter",
            "id": self._id("enc"),
            "status": status,
            "class": coding(ACT_CODE, class_code),
            "subject": self.subject,
            "period": {"start": start, **({"end": end} if end else {})},
        }
        if service:
            resource["serviceType"] = concept(coding(SYNTHETIC_LOCAL, service))
        if reasons:
            resource["reasonCode"] = [concept(coding(ICD10CM, c, d)) for c, d in reasons]
        return self._add(resource)

    def observation(
        self,
        code: str,
        display: str,
        effective: str,
        *,
        value: int | None = None,
        value_code: tuple[str, str] | None = None,
        members: tuple[str, ...] = (),
        status: str = "final",
    ) -> str:
        resource: Resource = {
            "resourceType": "Observation",
            "id": self._id("obs"),
            "status": status,
            "category": [
                concept(
                    coding("http://terminology.hl7.org/CodeSystem/observation-category", "survey")
                )
            ],
            "code": concept(coding(LOINC, code, display)),
            "subject": self.subject,
            "effectiveDateTime": effective,
        }
        if value is not None:
            resource["valueQuantity"] = {
                "value": value,
                "unit": "{score}",
                "system": "http://unitsofmeasure.org",
                "code": "{score}",
            }
        if value_code is not None:
            resource["valueCodeableConcept"] = concept(coding(LOINC, *value_code))
        if members:
            resource["hasMember"] = [{"reference": f"Observation/{m}"} for m in members]
        return self._add(resource)

    def questionnaire_response(
        self, questionnaire: str, authored: str, answers: dict[str, int]
    ) -> str:
        return self._add(
            {
                "resourceType": "QuestionnaireResponse",
                "id": self._id("qr"),
                "status": "completed",
                "questionnaire": questionnaire,
                "subject": self.subject,
                "authored": authored,
                "item": [
                    {"linkId": link, "answer": [{"valueInteger": value}]}
                    for link, value in answers.items()
                ],
            }
        )

    def medication_request(
        self,
        rxnorm: str,
        display: str,
        authored: str,
        *,
        days: int = 30,
        status: str = "completed",
        reason: tuple[str, str] | None = None,
    ) -> str:
        resource: Resource = {
            "resourceType": "MedicationRequest",
            "id": self._id("medreq"),
            "status": status,
            "intent": "order",
            "medicationCodeableConcept": concept(coding(RXNORM, rxnorm, display)),
            "subject": self.subject,
            "authoredOn": authored,
            "dispenseRequest": {
                "expectedSupplyDuration": {
                    "value": days,
                    "unit": "days",
                    "system": "http://unitsofmeasure.org",
                    "code": "d",
                }
            },
        }
        if reason:
            resource["reasonCode"] = [concept(coding(ICD10CM, *reason))]
        return self._add(resource)

    def medication_dispense(
        self,
        request_id: str | None,
        rxnorm: str,
        display: str,
        handed_over: str,
        *,
        days: int | None = 30,
    ) -> str:
        medication_id = self._add(
            {
                "resourceType": "Medication",
                "id": self._id("med"),
                "code": concept(coding(RXNORM, rxnorm, display)),
            }
        )
        resource: Resource = {
            "resourceType": "MedicationDispense",
            "id": self._id("meddisp"),
            "status": "completed",
            "medicationReference": {"reference": f"Medication/{medication_id}"},
            "subject": self.subject,
        }
        if request_id is not None:
            resource["authorizingPrescription"] = [{"reference": f"MedicationRequest/{request_id}"}]
        resource["whenHandedOver"] = handed_over
        if days is not None:
            resource["daysSupply"] = {
                "value": days,
                "unit": "days",
                "system": "http://unitsofmeasure.org",
                "code": "d",
            }
        return self._add(resource)

    def medication_statement(
        self,
        rxnorm: str,
        display: str,
        start: str,
        end: str | None = None,
        *,
        status: str = "active",
        reason: tuple[str, str] | None = None,
    ) -> str:
        resource: Resource = {
            "resourceType": "MedicationStatement",
            "id": self._id("medstmt"),
            "status": status,
            "medicationCodeableConcept": concept(coding(RXNORM, rxnorm, display)),
            "subject": self.subject,
            "effectivePeriod": {"start": start, **({"end": end} if end else {})},
        }
        if reason:
            resource["reasonCode"] = [concept(coding(ICD10CM, *reason))]
        return self._add(resource)

    def service_request(self, code: str, authored: str, *, status: str, reason: str) -> str:
        return self._add(
            {
                "resourceType": "ServiceRequest",
                "id": self._id("sr"),
                "status": status,
                "intent": "order",
                "code": concept(coding(SYNTHETIC_LOCAL, code)),
                "reasonCode": [concept(coding(ICD10CM, reason))],
                "subject": self.subject,
                "authoredOn": authored,
            }
        )

    def flag(self, code: str, start: str, *, status: str = "active") -> str:
        return self._add(
            {
                "resourceType": "Flag",
                "id": self._id("flag"),
                "status": status,
                "code": concept(coding(SYNTHETIC_LOCAL, code)),
                "subject": self.subject,
                "period": {"start": start},
            }
        )

    def bundle(self) -> Resource:
        return {
            "resourceType": "Bundle",
            "id": f"{self.key}-bundle",
            "meta": {"tag": [HTEST]},
            "type": "collection",
            "entry": [{"resource": r} for r in self.resources],
        }
