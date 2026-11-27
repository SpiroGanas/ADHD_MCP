"""Standing invariant 3: every signal cites at least one FHIR resource ID."""

from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from adhd_mcp.models.domain import EvidenceItem, ResourceRef

refs = st.builds(
    ResourceRef,
    resource_type=st.sampled_from(["Condition", "Observation", "Encounter"]),
    id=st.text(min_size=1, max_size=20),
)


@given(references=st.lists(refs, max_size=4), signal=st.text(min_size=1, max_size=30))
def test_evidence_item_exists_only_with_a_resource_reference(
    references: list[ResourceRef], signal: str
) -> None:
    try:
        item = EvidenceItem(signal=signal, references=references)
    except ValidationError:
        assert references == []
    else:
        assert len(item.references) >= 1
        assert all(ref.id for ref in item.references)
