"""A fixture adapter whose searches of chosen resource types fail, as a down server would."""

from typing import Any

from adhd_mcp.fhir.errors import FhirRequestError
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.port import SearchResult, SearchType
from tests.personas.builder import PersonaBuilder


class FailingAdapter(FixtureFhirAdapter):
    def __init__(self, p: PersonaBuilder, failing: set[str]) -> None:
        super().__init__(p.resources)
        self.failing = failing

    async def search(self, resource_type: SearchType, patient_id: str, **kw: Any) -> SearchResult:
        if resource_type in self.failing:
            raise FhirRequestError(f"search {resource_type}: failed", status=503, transient=True)
        return await super().search(resource_type, patient_id, **kw)
