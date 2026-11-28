"""Search semantics shared by every adapter.

``since`` keeps resources whose clinical date ends on or after that day, which is FHIR's
``ge`` search on the parameter below. Resources without that date are not returned by a
windowed search, as on a FHIR server; search without ``since`` to see everything.
"""

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from adhd_mcp.fhir.codes import canonical_system
from adhd_mcp.fhir.dates import DateRange, parse_fhir_date, parse_period

#: (system, code) pairs a search may be restricted to (FHIR ``code`` token search).
type Codes = tuple[tuple[str, str], ...]

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


def _well_formed(concept: Any) -> bool:
    """A CodeableConcept whose codings can be read (codes and systems strings or absent)."""
    if not isinstance(concept, dict):
        return False
    codings = concept.get("coding") or []
    return isinstance(codings, list) and all(
        isinstance(c, dict)
        and isinstance(c.get("code", ""), str)
        and isinstance(c.get("system", ""), str)
        for c in codings
    )


def _codings(concept: Any) -> list[dict[str, Any]]:
    codings = concept.get("coding") if isinstance(concept, dict) else None
    return [c for c in codings or [] if isinstance(c, dict)]


def matches_filters(resource: Mapping[str, Any], categories: tuple[str, ...], codes: Codes) -> bool:
    """FHIR ``category`` and ``code`` token search, as a local filter: any category code in
    ``categories`` (any system), and any ``code`` coding in ``codes``. A resource too
    malformed to tell is kept, so normalization reports it rather than it vanishing."""
    if categories:
        concepts = resource.get("category") or []
        if not isinstance(concepts, list) or not all(_well_formed(k) for k in concepts):
            return True
        found = {c.get("code") for k in concepts for c in _codings(k)}
        if not found & set(categories):
            return False
    if codes:
        concept = resource.get("code")
        if concept is not None and not _well_formed(concept):
            return True
        have = {
            (canonical_system(c.get("system")), str(c.get("code") or "").strip())
            for c in _codings(concept)
        }
        if not have & set(codes):
            return False
    return True


def matches_updated_since(resource: Mapping[str, Any], updated_since: datetime) -> bool:
    last_updated = (resource.get("meta") or {}).get("lastUpdated")
    if not last_updated:
        return False
    return datetime.fromisoformat(last_updated) >= updated_since
