"""Standing invariants 1 to 3 over generated records, through the whole assessment:
no diagnostic language, a safety gate in every result (a positive one always wins), every
signal cites a resource, and an excluded patient never receives a recommendation."""

import asyncio
from datetime import UTC, date, datetime, timedelta

from hypothesis import event, given, settings
from hypothesis import strategies as st

from adhd_mcp.clock import FixedClock
from adhd_mcp.conditions.adhd import adhd_plugin
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import RecommendationCode, SafetyGateStatus
from adhd_mcp.orchestration.assess import assess
from adhd_mcp.terminology.site_codes import load_site_codes
from adhd_mcp.tools.assessment import build_output
from adhd_mcp.tools.common import PatientRequest
from adhd_mcp.tools.context import ToolContext
from tests.helpers.wording import assert_no_diagnostic_language
from tests.personas.builder import PersonaBuilder

AS_OF = date(2026, 6, 15)
SITE = load_site_codes("synthetic")
CONTEXT = ToolContext(
    port=None, clock=FixedClock(datetime(2026, 6, 15, tzinfo=UTC)), site_codes=SITE
)

SIGNAL_CODES = [
    "F15.10", "F10.20", "Y90.3", "R78.0", "F12.20", "F43.10", "F63.81", "F33.1", "F41.1",
    "F60.3", "G47.00", "R41.840", "Z65.1", "Z56.0", "Z59.01", "Z81.8", "S06.0X1A", "I10",
]  # fmt: skip
INJURY_CODES = ["S62.302A", "V43.52XA", "V43.62XA", "W01.0XXA"]
SELF_HARM = ["R45.851", "T42.4X2A", "Z91.51"]
EXCLUDING = ["F90.0"]

days = st.integers(min_value=-10, max_value=1500)
records = st.fixed_dictionaries(
    {
        "conditions": st.lists(
            st.tuples(st.sampled_from(SIGNAL_CODES + SELF_HARM + EXCLUDING), days), max_size=8
        ),
        "injury_visits": st.lists(st.tuples(st.sampled_from(INJURY_CODES), days), max_size=4),
        "antidepressants": st.lists(
            st.tuples(st.sampled_from(["36437", "4493", "42347", "72625"]), days), max_size=4
        ),
    }
)


def build(spec: dict[str, list[tuple[str, int]]]) -> PersonaBuilder:
    p = PersonaBuilder("h02", gender="female", birth_date="1990-01-01")

    def ago(d: int) -> str:
        return (AS_OF - timedelta(days=d)).isoformat()

    for code, d in spec["conditions"]:
        p.condition(code, "generated", recorded=ago(d))
    for code, d in spec["injury_visits"]:
        visit = p.encounter("EMER", f"{ago(d)}T10:00:00Z")
        p.condition(code, "generated", recorded=ago(d), encounter=visit)
    for code, d in spec["antidepressants"]:
        request = p.medication_request(code, "generated", ago(d), days=60)
        p.medication_dispense(request, code, "generated", ago(d), days=60)
    return p


@settings(max_examples=120, deadline=None)
@given(spec=records)
def test_assessment_invariants_hold_for_generated_records(
    spec: dict[str, list[tuple[str, int]]],
) -> None:
    p = build(spec)
    records_ = PatientRecords(FixtureFhirAdapter(p.resources))
    result = asyncio.run(assess(adhd_plugin(), records_, p.patient_id, AS_OF, SITE))
    request = PatientRequest(
        patient_id=p.patient_id,
        as_of=AS_OF,
        patient=asyncio.run(records_.patient(p.patient_id)),
        records=records_,
    )
    # Building the output runs every model validator (gate consistency, basis, references).
    out = build_output(CONTEXT, request, "adhd", result)
    event(f"recommendation: {out.recommendation}")

    assert out.safety_gate is not None
    if out.safety_gate.status is SafetyGateStatus.POSITIVE:
        assert out.recommendation is RecommendationCode.ADDRESS_SAFETY_GATE_FIRST
    if out.excluded is True:
        assert out.recommendation is not RecommendationCode.CONSIDER_REFERRAL
    for finding in out.signals_checked:
        if finding.present:
            assert finding.references
    for item in out.basis:
        assert item.references
    assert_no_diagnostic_language(out.model_dump(mode="json"))
