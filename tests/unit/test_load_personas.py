import pytest
from scripts.load_personas import load, transaction

from tests.personas import all_resources


def test_refuses_to_load_into_a_non_local_server() -> None:
    with pytest.raises(SystemExit, match="non-local"):
        load("https://fhir.hospital.example/r4")


def test_transaction_puts_every_persona_resource_at_its_own_id() -> None:
    bundle = transaction()
    assert bundle["type"] == "transaction"
    assert len(bundle["entry"]) == len(all_resources())
    for entry in bundle["entry"]:
        resource = entry["resource"]
        assert entry["request"] == {
            "method": "PUT",
            "url": f"{resource['resourceType']}/{resource['id']}",
        }
