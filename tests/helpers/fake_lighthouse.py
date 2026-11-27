"""An in-process stand-in for the VA Lighthouse Patient Health API (FHIR R4), shaped after its
public sandbox CapabilityStatement and OpenAPI description (fetched 2026-11-27).

Differences from ``FakeFhirServer`` that the Lighthouse adapter must cope with:

* only the resource types Lighthouse offers; any other type is 404;
* no ``_include``, and no date search on MedicationRequest: either parameter is a 400, which
  proves the adapter never sends one;
* medication searches return no Medication resources; ``GET Medication/{id}`` serves them;
* every reference in a response is an absolute URL;
* next links carry a ``-pageToken``.
"""

import base64
import json
from collections.abc import Iterable
from typing import Any

import httpx2

from adhd_mcp.fhir.port import RawResource
from tests.helpers.fake_fhir_server import FakeFhirServer

LIGHTHOUSE_BASE = "https://sandbox.lighthouse.test/services/fhir/v0/r4"
TOKEN_URL = "https://sandbox.lighthouse.test/oauth2/health/system/v1/token"

OFFERED = frozenset({"Condition", "Observation", "Encounter", "Procedure", "MedicationRequest"})
#: Search parameters the fake accepts, per type (a subset of the recorded statement).
PARAMS = {
    "Condition": {"patient", "_count", "recorded-date", "_lastUpdated", "-pageToken"},
    "Observation": {"patient", "_count", "date", "_lastUpdated", "-pageToken"},
    "Encounter": {"patient", "_count", "date", "_lastUpdated", "-pageToken"},
    "Procedure": {"patient", "_count", "date", "_lastUpdated", "-pageToken"},
    "MedicationRequest": {"patient", "_count", "_lastUpdated", "-pageToken"},
}


def absolute(value: Any, base: str) -> Any:
    """Rewrite every relative ``Type/id`` reference to ``{base}/Type/id``."""
    if isinstance(value, dict):
        return {
            k: (
                f"{base}/{v}"
                if k == "reference" and isinstance(v, str) and not v.startswith(("#", "http"))
                else absolute(v, base)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [absolute(v, base) for v in value]
    return value


class FakeLighthouseServer(FakeFhirServer):
    def __init__(self, resources: Iterable[RawResource], *, page_size: int = 3) -> None:
        resources = list(resources)
        super().__init__(resources, page_size=page_size, base=LIGHTHOUSE_BASE)
        self.medications = {r["id"]: r for r in resources if r.get("resourceType") == "Medication"}
        self.tokens: list[dict[str, str]] = []
        self.required_token: str | None = None
        #: Requests refused for naming a type or parameter Lighthouse does not offer.
        self.rejected: list[httpx2.Request] = []

    def transport(self) -> httpx2.MockTransport:
        return httpx2.MockTransport(self.route)

    async def route(self, request: httpx2.Request) -> httpx2.Response:  # noqa: PLR0911
        if str(request.url) == TOKEN_URL:
            return self._token(request)
        self.requests.append(request)
        if self.required_token is not None and request.headers.get("Authorization") != (
            f"Bearer {self.required_token}"
        ):
            return httpx2.Response(401)
        path = request.url.path.removeprefix(httpx2.URL(LIGHTHOUSE_BASE).path).strip("/")
        parts = path.split("/")
        if len(parts) == 2 and parts[0] == "Medication":
            medication = self.medications.get(parts[1])
            if medication is None:
                return httpx2.Response(404, json={"resourceType": "OperationOutcome"})
            return httpx2.Response(200, json=medication)
        if len(parts) == 1 and parts[0] != "Patient":
            if parts[0] not in OFFERED:
                self.rejected.append(request)
                return httpx2.Response(404, json={"resourceType": "OperationOutcome"})
            if not set(request.url.params) <= PARAMS[parts[0]]:
                self.rejected.append(request)
                return httpx2.Response(400, json={"resourceType": "OperationOutcome"})
        response = await self.respond(_translate_page_token(request))
        if response.status_code != 200:
            return response
        body = response.json()
        if body.get("resourceType") == "Bundle":
            body["entry"] = [
                e for e in body["entry"] if e["resource"]["resourceType"] != "Medication"
            ]
            for link in body["link"]:
                link["url"] = link["url"].replace("_offset=", "-pageToken=")
        return httpx2.Response(200, json=absolute(body, LIGHTHOUSE_BASE))

    def _token(self, request: httpx2.Request) -> httpx2.Response:
        form = dict(httpx2.QueryParams(request.content.decode()))
        self.tokens.append(form)
        token = f"token-{len(self.tokens)}"
        return httpx2.Response(
            200, json={"access_token": token, "token_type": "Bearer", "expires_in": 300}
        )


def launch_patient(form: dict[str, str]) -> str | None:
    """The patient a token request's ``launch`` parameter names."""
    if "launch" not in form:
        return None
    return str(json.loads(base64.b64decode(form["launch"]))["patient"])


def _translate_page_token(request: httpx2.Request) -> httpx2.Request:
    """The base fake pages by ``_offset``; Lighthouse's links say ``-pageToken``."""
    params = dict(request.url.params)
    if "-pageToken" in params:
        params["_offset"] = params.pop("-pageToken")
    url = request.url.copy_with(params=params)
    return httpx2.Request(request.method, url, headers=request.headers)
