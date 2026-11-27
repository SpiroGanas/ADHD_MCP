"""SMART on FHIR backend services (client credentials with a signed JWT assertion).

The server authenticates to the FHIR server with its own registered credentials. A caller's
MCP token is never forwarded: this module only ever sends the server's own assertion and
the access token it receives.
"""

import asyncio
import uuid
from datetime import timedelta

import httpx2
import jwt

from adhd_mcp.clock import Clock
from adhd_mcp.fhir.errors import FhirRequestError

ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
#: Refresh this long before the token expires.
_EARLY = timedelta(seconds=60)


class SmartBackendAuth:
    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        private_key_pem: str,
        key_id: str,
        scope: str,
        clock: Clock,
        algorithm: str = "RS384",
        transport: httpx2.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        url = httpx2.URL(token_url)
        if url.scheme != "https" and url.host not in {"localhost", "127.0.0.1"}:
            raise ValueError("the SMART token URL must use https")
        if algorithm not in {"RS384", "ES384"}:
            raise ValueError("SMART backend services require RS384 or ES384")
        self._token_url = token_url
        self._client_id = client_id
        self._key = private_key_pem
        self._kid = key_id
        self._scope = scope
        self._clock = clock
        self._alg = algorithm
        self._client = httpx2.AsyncClient(transport=transport, timeout=timeout)
        self._token: str | None = None
        self._expires = clock.now()
        self._lock = asyncio.Lock()

    def assertion(self) -> str:
        now = self._clock.now()
        claims = {
            "iss": self._client_id,
            "sub": self._client_id,
            "aud": self._token_url,
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        }
        return jwt.encode(claims, self._key, algorithm=self._alg, headers={"kid": self._kid})

    async def access_token(self) -> str:
        async with self._lock:
            if self._token is not None and self._clock.now() < self._expires - _EARLY:
                return self._token
            form = {
                "grant_type": "client_credentials",
                "scope": self._scope,
                "client_assertion_type": ASSERTION_TYPE,
                "client_assertion": self.assertion(),
            }
            try:
                response = await self._client.post(self._token_url, data=form)
            except httpx2.HTTPError as exc:
                raise FhirRequestError("SMART token request failed", transient=True) from exc
            if response.status_code != 200:
                raise FhirRequestError(
                    f"SMART token request: HTTP {response.status_code}",
                    status=response.status_code,
                    transient=response.status_code >= 500,
                )
            body = response.json()
            token = body.get("access_token")
            if not isinstance(token, str) or body.get("token_type", "").lower() != "bearer":
                raise FhirRequestError(
                    "SMART token response is not a bearer token", transient=False
                )
            try:
                lifetime = int(body.get("expires_in", 300))
            except (TypeError, ValueError) as exc:
                raise FhirRequestError(
                    "SMART token response has a bad expiry", transient=False
                ) from exc
            self._token = token
            self._expires = self._clock.now() + timedelta(seconds=lifetime)
            return token

    def invalidate(self) -> None:
        """Forget the token (after a 401 from the FHIR server)."""
        self._token = None

    async def aclose(self) -> None:
        await self._client.aclose()
