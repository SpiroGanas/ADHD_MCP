"""Phase 8, item 6: with the dummy scorer present, absent or failing, every persona's
assessment is identical to the rules-only one, apart from the scorer reference itself."""

import dataclasses
from collections.abc import Sequence
from datetime import date

import pytest

from adhd_mcp.conditions.adhd import adhd_plugin
from adhd_mcp.conditions.base import ConditionPlugin
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.assessment import SignalFinding
from adhd_mcp.orchestration.assess import Assessment, assess
from adhd_mcp.rules.scorer import DummyScorer
from adhd_mcp.terminology.site_codes import load_site_codes
from tests.personas import all_resources, persona_ids

pytestmark = pytest.mark.anyio

AS_OF = date(2026, 6, 15)
SITE = load_site_codes("synthetic")


class FailingScorer:
    id = "failing"
    version = "0.0.0"

    def score(self, findings: Sequence[SignalFinding]) -> float | None:
        raise RuntimeError("scorer down")


def variants() -> dict[str, ConditionPlugin]:
    base = adhd_plugin()
    return {
        "rules-only": base,
        "absent": dataclasses.replace(base, scorer=None),
        "dummy": dataclasses.replace(base, scorer=DummyScorer()),
        "failing": dataclasses.replace(base, scorer=FailingScorer()),
    }


def without_scorer(a: Assessment) -> Assessment:
    return dataclasses.replace(a, scorer=None)


@pytest.mark.parametrize("persona_id", persona_ids())
async def test_a_scorer_never_changes_an_assessment(persona_id: str) -> None:
    records = PatientRecords(FixtureFhirAdapter(all_resources()))
    patient = f"{persona_id}-patient"
    results = {
        name: await assess(plugin, records, records, patient, AS_OF, site=SITE)
        for name, plugin in variants().items()
    }
    expected = without_scorer(results["rules-only"])
    for name, result in results.items():
        assert without_scorer(result) == expected, name
    assert results["absent"].scorer is None
    assert results["dummy"].scorer is not None
    assert results["dummy"].scorer.id == "dummy-not-a-model"
    assert results["failing"].scorer is not None
    assert results["failing"].scorer.failed is True
