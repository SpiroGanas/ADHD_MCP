"""The read-only FHIR port. The application reads patient data only through this interface.

There is deliberately no create, update, delete, transaction or operation method
(standing invariant 4).
"""

import re
from dataclasses import dataclass, field
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

#: OperationOutcome issue severities kept as warnings; "information" issues are not problems.
WARNING_SEVERITIES = frozenset({"fatal", "error", "warning"})


@dataclass(frozen=True)
class SearchWarning:
    """An OperationOutcome issue returned with a search, for example ``incomplete``,
    ``suppressed`` or ``too-costly``. Only the severity and issue code are kept; the
    server's diagnostic text is dropped (it may hold clinical content)."""

    severity: str
    code: str


@dataclass(frozen=True)
class SearchResult:
    """Resources found, plus any warnings the server returned with them."""

    resources: list[RawResource]
    warnings: tuple[SearchWarning, ...] = field(default=())


_FHIR_ID = re.compile(r"[A-Za-z0-9\-.]{1,64}")


def is_fhir_id(value: str) -> bool:
    """Whether ``value`` is a FHIR resource id, safe to put in a URL path."""
    return isinstance(value, str) and _FHIR_ID.fullmatch(value) is not None


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
    ) -> SearchResult:
        """All resources of one type for a patient, following every page.

        ``since`` keeps resources whose clinical date ends on or after that day
        (see ``adhd_mcp.fhir.search``). ``updated_since`` filters on ``meta.lastUpdated``.
        Medication searches also return the ``Medication`` resources they reference.
        Warnings mean the server may have returned less than everything (truncated,
        suppressed or withheld results); callers must disclose them.
        Raises ``FhirRequestError`` when the request fails, and ``SearchNotSupportedError``
        when the server does not offer the resource type at all; no resources means none
        found.
        """
        ...
