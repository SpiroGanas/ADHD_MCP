"""A FHIR adapter backed by resources in memory or bundle files. Used by most tests."""

import copy
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from adhd_mcp.fhir.errors import ResourceNotFoundError
from adhd_mcp.fhir.port import (
    RawResource,
    SearchResult,
    SearchType,
    SearchWarning,
    validate_patient_id,
)
from adhd_mcp.fhir.search import (
    MEDICATION_TYPES,
    Codes,
    matches_filters,
    matches_since,
    matches_updated_since,
)

_DEFAULT_LAST_UPDATED = datetime(2026, 1, 1, tzinfo=UTC)


class FixtureFhirAdapter:
    """Implements ``FhirReadPort`` over a fixed set of resources.

    Resources without ``meta.lastUpdated`` are stamped with ``last_updated``, as a server
    would stamp them on load. ``warnings`` simulates server OperationOutcome issues for a
    resource type, returned with every search of that type.
    """

    def __init__(
        self,
        resources: Iterable[RawResource],
        *,
        last_updated: datetime = _DEFAULT_LAST_UPDATED,
        warnings: Mapping[str, Sequence[SearchWarning]] | None = None,
    ) -> None:
        self._warnings = {k: tuple(v) for k, v in (warnings or {}).items()}
        self._by_key: dict[tuple[str, str], RawResource] = {}
        for raw in resources:
            resource = copy.deepcopy(raw)
            meta = resource.setdefault("meta", {})
            meta.setdefault("lastUpdated", last_updated.isoformat())
            self._by_key[(resource["resourceType"], resource["id"])] = resource

    @classmethod
    def from_directory(cls, directory: Path) -> "FixtureFhirAdapter":
        resources: list[RawResource] = []
        for path in sorted(directory.glob("*.json")):
            bundle = json.loads(path.read_text(encoding="utf-8"))
            resources.extend(entry["resource"] for entry in bundle.get("entry", []))
        return cls(resources)

    async def read_patient(self, patient_id: str) -> RawResource:
        validate_patient_id(patient_id)
        resource = self._by_key.get(("Patient", patient_id))
        if resource is None:
            raise ResourceNotFoundError(f"Patient/{patient_id} not found")
        return copy.deepcopy(resource)

    async def search(
        self,
        resource_type: SearchType,
        patient_id: str,
        *,
        since: date | None = None,
        updated_since: datetime | None = None,
        categories: tuple[str, ...] = (),
        codes: Codes = (),
    ) -> SearchResult:
        validate_patient_id(patient_id)
        subject = f"Patient/{patient_id}"
        found = [
            r
            for (rtype, _), r in self._by_key.items()
            if rtype == resource_type
            and (r.get("subject") or {}).get("reference") == subject
            and (since is None or matches_since(r, since))
            and (updated_since is None or matches_updated_since(r, updated_since))
            and matches_filters(r, categories, codes)
        ]
        if resource_type in MEDICATION_TYPES:
            found += self._referenced_medications(found)
        return SearchResult(
            resources=copy.deepcopy(found), warnings=self._warnings.get(resource_type, ())
        )

    def _referenced_medications(self, resources: list[RawResource]) -> list[RawResource]:
        out: dict[str, RawResource] = {}
        for resource in resources:
            reference = (resource.get("medicationReference") or {}).get("reference", "")
            kind, _, medication_id = reference.partition("/")
            if kind == "Medication" and ("Medication", medication_id) in self._by_key:
                out[medication_id] = self._by_key[("Medication", medication_id)]
        return list(out.values())
