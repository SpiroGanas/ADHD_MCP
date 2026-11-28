"""Peer review 01, T2: the property tests drew dotted ICD-10-CM codes from the value sets, so
"a self-harm signal is never lost" was checked only over encodings the matcher already
understood. Here the same recent suicidal-ideation fact is generated in many legal (and some
merely common) FHIR encodings. Invariant: the gate is positive, or it says it could not read
something (data_unavailable); it is never clear."""

import asyncio
from datetime import date, timedelta
from typing import Any

from hypothesis import event, given, settings
from hypothesis import strategies as st

from adhd_mcp.evidence.safety_gate import assess_safety_gate, load_gate_content
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.reader import PatientRecords
from adhd_mcp.models.domain import SafetyGateStatus
from adhd_mcp.terminology.site_codes import load_site_codes
from tests.personas.builder import PersonaBuilder

AS_OF = date(2026, 6, 15)
CONTENT = load_gate_content(load_site_codes("synthetic"), strict=True)
ICD = "http://hl7.org/fhir/sid/icd-10-cm"

codings = st.sampled_from(
    [
        [{"system": ICD, "code": "R45.851"}],
        [{"system": ICD, "code": "R45851"}],
        [{"system": ICD, "code": "r45.851"}],
        [{"system": "urn:oid:2.16.840.1.113883.6.90", "code": "R45.851"}],
        [{"system": f"{ICD}/", "code": "R45.851"}],
        [{"system": "http://snomed.info/sct", "code": "6471006"}],
        [
            {"system": "http://snomed.info/sct", "code": "6471006"},
            {"system": ICD, "code": "R45.851"},
        ],
        [{"code": "R45.851"}],
        [],
    ]
)
verification = st.sampled_from([None, "confirmed", "provisional", "unconfirmed", "differential"])


def dates(days: int) -> st.SearchStrategy[dict[str, Any]]:
    day = AS_OF - timedelta(days=days)
    return st.sampled_from(
        [
            {"recordedDate": day.isoformat()},
            {"recordedDate": f"{day.isoformat()}T10:00:00Z"},
            {"recordedDate": f"{day.isoformat()}T10:00:00"},
            {"recordedDate": f"{day.isoformat()}T10:00:00-05:00"},
            {"onsetDateTime": day.isoformat()},
            {"onsetPeriod": {"start": day.isoformat()}},
            {},
        ]
    )


@st.composite
def conditions(draw: st.DrawFn) -> dict[str, Any]:
    resource: dict[str, Any] = {
        "resourceType": "Condition",
        "id": "h02-cond-x",
        "subject": {"reference": "Patient/h02-patient"},
        "code": {"coding": draw(codings), "text": "free text"},
    }
    resource |= draw(dates(draw(st.integers(min_value=0, max_value=365))))
    status = draw(verification)
    if status is not None:
        resource["verificationStatus"] = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": status,
                }
            ]
        }
    return resource


@settings(max_examples=200, deadline=None)
@given(condition=conditions(), noise=st.integers(min_value=0, max_value=3))
def test_a_recent_self_harm_fact_is_never_read_as_clear(
    condition: dict[str, Any], noise: int
) -> None:
    p = PersonaBuilder("h02", gender="unknown", birth_date="1980")
    for _ in range(noise):
        p.condition("I10", "generated", recorded="2026-01-01")
    p.resources.append(condition)
    records = PatientRecords(FixtureFhirAdapter(p.resources))
    result, _ = asyncio.run(assess_safety_gate(records, p.patient_id, AS_OF, CONTENT))
    event(f"gate: {result.status}")
    assert result.status in {SafetyGateStatus.POSITIVE, SafetyGateStatus.DATA_UNAVAILABLE}
