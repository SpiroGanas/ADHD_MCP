"""Peer review 01, D1: an audit record lists every resource read, which for a long record can
be tens of thousands of references. Above a limit it records a count and a hash instead."""

from adhd_mcp.audit.middleware import MAX_LISTED_RESOURCES, CallAudit


def audit_of(n: int) -> CallAudit:
    audit = CallAudit()
    for i in range(n):
        audit.add({"resourceType": "Observation", "id": f"o{i:05d}"})
    return audit


def test_a_short_list_is_kept_whole_with_its_count() -> None:
    listed, count, digest = audit_of(3).resource_summary()
    assert [r.id for r in listed] == ["o00000", "o00001", "o00002"]
    assert (count, digest) == (3, None)


def test_a_long_list_becomes_a_count_and_a_hash() -> None:
    listed, count, digest = audit_of(MAX_LISTED_RESOURCES + 1).resource_summary()
    assert listed == []
    assert count == MAX_LISTED_RESOURCES + 1
    assert digest is not None
    assert len(digest) == 64


def test_the_hash_depends_only_on_what_was_read() -> None:
    first = audit_of(MAX_LISTED_RESOURCES + 5).resource_summary()[2]
    again = audit_of(MAX_LISTED_RESOURCES + 5).resource_summary()[2]
    other = audit_of(MAX_LISTED_RESOURCES + 6).resource_summary()[2]
    assert first == again
    assert first != other
