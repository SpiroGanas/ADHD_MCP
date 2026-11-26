"""The read-only FHIR port. The application reads patient data only through this interface.

There is deliberately no create, update, delete, transaction or operation method
(standing invariant 4).
"""

import re
from datetime import date, datetime
from typing import Any, Literal, Protocol, get_args

RawResource = dict[str, Any]

SearchType = Literal[
    "Condition",
    "Observation",
    "QuestionnaireResponse",
    "MedicationRequest",
    "MedicationDispense",
    "MedicationStatement",
    "Encounter",
    "Procedure",
    "ServiceRequest",
    "CarePlan",
    "Flag",
]
SEARCHABLE_TYPES: tuple[SearchType, ...] = get_args(SearchType)

_FHIR_ID = re.compile(r"[A-Za-z0-9\-.]{1,64}")


def validate_patient_id(patient_id: str) -> str:
    """Reject anything that is not a FHIR resource id, before it reaches a URL."""
    if not isinstance(patient_id, str) or _FHIR_ID.fullmatch(patient_id) is None:
        raise ValueError("invalid patient id: must be 1-64 letters, digits, '-' or '.'")
    return patient_id


class FhirReadPort(Protocol):
    async def read_patient(self, patient_id: str) -> RawResource:
        """The Patient resource. Raises ``ResourceNotFoundError`` if it does not exist."""
        ...

    async def search(
        self,
        resource_type: SearchType,
        patient_id: str,
        *,
        since: date | None = None,
        updated_since: datetime | None = None,
    ) -> list[RawResource]:
        """All resources of one type for a patient, following every page.

        ``since`` keeps resources whose clinical date ends on or after that day
        (see ``adhd_mcp.fhir.search``). ``updated_since`` filters on ``meta.lastUpdated``.
        Medication searches also return the ``Medication`` resources they reference.
        Raises ``FhirRequestError`` when the request fails; an empty list means none found.
        """
        ...
