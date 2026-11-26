"""Load every persona into a local FHIR server for integration tests.

Usage: uv run python scripts/load_personas.py [--url http://localhost:8080/fhir]

This test tool writes (a transaction of PUTs). It is not part of the server, which is
read-only. It refuses any host other than loopback (localhost) unless --allow-remote-test-server
is given, so synthetic data is never pushed to a real system by accident.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import httpx2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.personas import load_bundle, persona_ids  # noqa: E402

DEFAULT_URL = "http://localhost:8080/fhir"
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def transaction() -> dict[str, Any]:
    entries = []
    for persona_id in persona_ids():
        for entry in load_bundle(persona_id)["entry"]:
            resource = entry["resource"]
            path = f"{resource['resourceType']}/{resource['id']}"
            entries.append({"resource": resource, "request": {"method": "PUT", "url": path}})
    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}


def wait_until_ready(client: httpx2.Client, url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            if client.get(f"{url}/metadata").status_code == 200:
                return
        except httpx2.TransportError:
            pass
        if time.monotonic() > deadline:
            raise SystemExit(f"FHIR server at {url} not ready after {timeout:.0f}s")
        time.sleep(2)


def load(url: str = DEFAULT_URL, *, allow_remote: bool = False, timeout: float = 300) -> int:
    host = httpx2.URL(url).host
    if host not in LOCAL_HOSTS and not allow_remote:
        raise SystemExit(f"refusing to load test data into non-local host {host!r}")
    bundle = transaction()
    with httpx2.Client(timeout=120, headers={"Content-Type": "application/fhir+json"}) as client:
        wait_until_ready(client, url, timeout)
        response = client.post(url, json=bundle)
        if response.status_code >= 300:
            raise SystemExit(f"loading failed with HTTP {response.status_code}")
    return len(bundle["entry"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--allow-remote-test-server", action="store_true")
    args = parser.parse_args()
    count = load(args.url, allow_remote=args.allow_remote_test_server)
    print(f"Loaded {count} synthetic resources into {args.url}")


if __name__ == "__main__":
    main()
