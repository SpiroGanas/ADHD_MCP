"""VA Lighthouse Patient Health API (FHIR R4): the profile-driven HTTP adapter and its OAuth
client credentials grant (CCG), built from the public documentation (Phase 8, item 1).

Lighthouse's CCG differs from SMART backend services in three ways (developer.va.gov, client
credentials page, read 2026-11-27):

* when the scopes include ``launch``, the token request carries ``launch``, the base64 of
  ``{"patient": "<ICN>"}``, so each token is for one patient: tokens are kept per patient;
* the assertion's audience is an authorization-server URL given at registration, not the
  token URL (``ADHD_MCP_SMART_AUDIENCE``);
* the documentation's example signs with RS256; the assertion may live at most 300 seconds.

Not verified here (no sandbox credentials): the exact scope names and audience URL for this
API. Both are settings, and docs/integration/lighthouse.md says what to check on registration.
"""

import asyncio
import base64
import json
from collections import OrderedDict
from datetime import datetime

import httpx2

from adhd_mcp.clock import Clock
from adhd_mcp.fhir.errors import FhirRequestError
from adhd_mcp.fhir.http_adapter import HttpFhirAdapter, Sleep
from adhd_mcp.fhir.profiles import load_server_profile
from adhd_mcp.fhir.smart import _EARLY, FhirAuth, SmartBackendAuth


def launch_value(patient_id: str) -> str:
    """Lighthouse's ``launch`` parameter: base64 of compact JSON naming the patient."""
    payload = json.dumps({"patient": patient_id}, separators=(",", ":"))
    return base64.b64encode(payload.encode()).decode()


class LighthouseCcgAuth(SmartBackendAuth):
    """Client credentials grant with patient-scoped tokens (when the scopes say ``launch``)."""

    ALGORITHMS = frozenset({"RS256", "RS384", "ES384"})
    #: Tokens kept at most, one per patient; the oldest is dropped first.
    max_cached = 128

    def __init__(
        self,
        *,
        token_url: str,
        audience: str | None,
        client_id: str,
        private_key_pem: str,
        key_id: str,
        scope: str,
        clock: Clock,
        algorithm: str = "RS256",
        transport: httpx2.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        if not audience:
            raise ValueError("a Lighthouse client assertion needs its audience")
        super().__init__(
            token_url=token_url,
            audience=audience,
            client_id=client_id,
            private_key_pem=private_key_pem,
            key_id=key_id,
            scope=scope,
            clock=clock,
            algorithm=algorithm,
            transport=transport,
            timeout=timeout,
        )
        self._patient_scoped = "launch" in self._scope.split()
        self._tokens: OrderedDict[str, tuple[str, datetime]] = OrderedDict()
        self._patient_locks: dict[str, asyncio.Lock] = {}

    async def access_token(self, patient_id: str | None = None) -> str:
        if not self._patient_scoped:
            return await super().access_token(patient_id)
        if patient_id is None:
            raise FhirRequestError(
                "Lighthouse token request: a patient-scoped token needs a patient",
                transient=False,
            )
        lock = self._patient_locks.setdefault(patient_id, asyncio.Lock())
        async with lock:
            held = self._tokens.get(patient_id)
            if held is not None and self._clock.now() < held[1] - _EARLY:
                self._tokens.move_to_end(patient_id)
                return held[0]
            token, expires = await self._request_token({"launch": launch_value(patient_id)})
            self._tokens[patient_id] = (token, expires)
            self._tokens.move_to_end(patient_id)
            while len(self._tokens) > self.max_cached:
                self._tokens.popitem(last=False)
            if len(self._patient_locks) > 2 * self.max_cached:
                self._patient_locks = {
                    k: v for k, v in self._patient_locks.items() if k in self._tokens or v.locked()
                }
            return token

    def invalidate(self, patient_id: str | None = None) -> None:
        if not self._patient_scoped:
            super().invalidate(patient_id)
        elif patient_id is not None:
            self._tokens.pop(patient_id, None)


def lighthouse_adapter(
    base_url: str,
    *,
    auth: FhirAuth | None = None,
    transport: httpx2.AsyncBaseTransport | None = None,
    page_size: int = 100,
    sleep: Sleep = asyncio.sleep,
) -> HttpFhirAdapter:
    """The HTTP adapter with the Lighthouse profile."""
    return HttpFhirAdapter(
        base_url,
        transport=transport,
        page_size=page_size,
        sleep=sleep,
        auth=auth,
        profile=load_server_profile("lighthouse"),
    )
