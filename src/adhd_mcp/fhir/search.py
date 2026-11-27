"""Search semantics shared by every adapter.

``since`` keeps resources whose clinical date ends on or after that day, which is FHIR's
``ge`` search on the parameter below. Resources without that date are not returned by a
windowed search, as on a FHIR server; search without ``since`` to see everything.
"""

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from adhd_mcp.fhir.dates import DateRange, parse_fhir_date, parse_period

#: resource type -> (FHIR search parameter, element name, element kind)
DATE_SEARCH: dict[str, tuple[str, str, str]] = {
    "Condition": ("recorded-date", "recordedDate", "date"),
    "Observation": ("date", "effective", "choice"),
    "QuestionnaireResponse": ("authored", "authored", "date"),
    "MedicationRequest": ("authoredon", "authoredOn", "date"),
    "MedicationDispense": ("whenhandedover", "whenHandedOver", "date"),
    "MedicationStatement": ("effective", "effective", "choice"),
    "Encounter": ("date", "period", "period"),
    "Procedure": ("date", "performed", "choice"),
    "ServiceRequest": ("authored", "authoredOn", "date"),
    "CarePlan": ("date", "period", "period"),
    "Flag": ("date", "period", "period"),
}

MEDICATION_TYPES = frozenset({"MedicationRequest", "MedicationDispense", "MedicationStatement"})


def clinical_date(resource: Mapping[str, Any]) -> DateRange | None:
    """The date the ``since`` filter applies to, or ``None`` if the resource has none."""
    _, element, kind = DATE_SEARCH[resource["resourceType"]]
    if kind == "date":
        value = resource.get(element)
        return parse_fhir_date(value) if value else None
    if kind == "period":
        period = resource.get(element)
        return parse_period(period) if period else None
    for suffix in ("DateTime", "Date", "Instant"):
        if resource.get(element + suffix):
            return parse_fhir_date(resource[element + suffix])
    period = resource.get(element + "Period")
    return parse_period(period) if period else None


def matches_since(resource: Mapping[str, Any], since: date) -> bool:
    when = clinical_date(resource)
    return when is not None and when.ends_on_or_after(since)


def matches_updated_since(resource: Mapping[str, Any], updated_since: datetime) -> bool:
    last_updated = (resource.get("meta") or {}).get("lastUpdated")
    if not last_updated:
        return False
    return datetime.fromisoformat(last_updated) >= updated_since
