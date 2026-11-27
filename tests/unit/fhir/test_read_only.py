"""Standing invariant 4: no tool or adapter can write to a FHIR server.

Behavioural proof is in tests/adapters (every request the HTTP adapter makes is a GET).
These structural checks stop a write path from being added quietly.
"""

import inspect
import re
from pathlib import Path

import adhd_mcp
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter
from adhd_mcp.fhir.port import FhirReadPort

READ_METHODS = {"read_patient", "search"}
SOURCE_ROOT = Path(adhd_mcp.__file__).parent
WRITE_CALL = re.compile(
    r"\.(post|put|patch|delete)\(|method\s*=\s*[\"'](POST|PUT|PATCH|DELETE)[\"']"
    r"|[\"'](POST|PUT|PATCH|DELETE)[\"']\s*,",
    re.IGNORECASE,
)


def public_methods(cls: type) -> set[str]:
    return {
        name
        for name, member in inspect.getmembers(cls)
        if not name.startswith("_") and callable(member)
    }


def test_port_declares_only_read_methods() -> None:
    assert public_methods(FhirReadPort) == READ_METHODS


def test_adapters_expose_no_write_methods() -> None:
    assert public_methods(FixtureFhirAdapter) == READ_METHODS | {"from_directory"}
    assert public_methods(HttpFhirAdapter) == READ_METHODS | {"aclose"}


#: The only POST allowed anywhere: the SMART backend-services token request, which goes to
#: the OAuth token endpoint, never to the FHIR server (behaviour: tests/unit/fhir/test_smart.py).
#: Adding an entry here needs the project owner's review.
ALLOWED_WRITES = {("fhir/smart.py", "response = await self._client.post(self._token_url, data=form)")}


def test_no_source_file_issues_an_http_write() -> None:
    offenders = [
        f"{path.relative_to(SOURCE_ROOT)}:{n}"
        for path in SOURCE_ROOT.rglob("*.py")
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if WRITE_CALL.search(line)
        and (str(path.relative_to(SOURCE_ROOT)), line.strip()) not in ALLOWED_WRITES
    ]
    assert offenders == []


def test_every_allowed_write_still_exists() -> None:
    for relative, line in ALLOWED_WRITES:
        source = (SOURCE_ROOT / relative).read_text(encoding="utf-8")
        assert line in [x.strip() for x in source.splitlines()], relative


def test_write_pattern_detects_write_calls() -> None:
    assert WRITE_CALL.search("await client.post(url, json=x)")
    assert WRITE_CALL.search('client.request(method="PUT", url=u)')
    assert WRITE_CALL.search('client.request("DELETE", u)')
    assert not WRITE_CALL.search("await client.get(url)")
