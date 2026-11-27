"""A FHIR R4 adapter over HTTP. Read-only: it issues GET requests and nothing else.

* Search follows ``next`` links to the end, but only within the configured server's origin
  and base path (a server cannot redirect the client elsewhere), and at most ``max_pages``.
* OperationOutcome issues of severity warning or worse, on any page, are returned as
  ``SearchWarning`` (severity and issue code only; diagnostic text is dropped).
* Resources of the searched type without an id are passed on, so normalization reports
  them as skipped instead of their vanishing here.
* Timeouts, connection errors, 429 and 5xx are retried with exponential backoff; a numeric
  ``Retry-After`` is honoured up to ``max_backoff``. Other failures are not retried.
* A missing patient (404 or 410) raises ``ResourceNotFoundError``; every other failure
  raises ``FhirRequestError``. Error messages never include response bodies.

Unauthenticated at this stage; SMART backend-services credentials arrive in Phase 6.
"""

import asyncio
import re
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from types import TracebackType
from typing import Any, Self

import httpx2

from adhd_mcp.fhir.errors import FhirRequestError, ResourceNotFoundError
from adhd_mcp.fhir.port import (
    WARNING_SEVERITIES,
    RawResource,
    SearchResult,
    SearchType,
    SearchWarning,
    validate_patient_id,
)
from adhd_mcp.fhir.search import DATE_SEARCH, MEDICATION_TYPES

_TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})
_NOT_FOUND_STATUSES = frozenset({404, 410})
_FHIR_JSON = "application/fhir+json"
_ISSUE_CODE = re.compile(r"[a-z][a-z-]{0,31}")

Sleep = Callable[[float], Awaitable[None]]


class HttpFhirAdapter:
    """Implements ``FhirReadPort`` against a FHIR R4 server."""

    def __init__(
        self,
        base_url: str,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
        max_attempts: int = 4,
        backoff_base: float = 0.5,
        max_backoff: float = 8.0,
        page_size: int = 100,
        max_pages: int = 1000,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        url = httpx2.URL(base_url.rstrip("/"))
        if url.scheme not in {"http", "https"} or not url.host:
            raise ValueError("FHIR base URL must be an absolute http or https URL")
        self._base = url
        self._client = httpx2.AsyncClient(
            transport=transport,
            timeout=timeout,
            headers={"Accept": _FHIR_JSON},
            follow_redirects=False,
        )
        self._max_attempts = max_attempts
        self._backoff_base = backoff_base
        self._max_backoff = max_backoff
        self._page_size = page_size
        self._max_pages = max_pages
        self._sleep = sleep

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _url(self, path: str) -> httpx2.URL:
        return httpx2.URL(f"{self._base}/{path}")

    def _same_origin(self, url: httpx2.URL) -> bool:
        return (
            url.scheme == self._base.scheme
            and url.host == self._base.host
            and url.port == self._base.port
            and (url.path == self._base.path or url.path.startswith(self._base.path + "/"))
        )

    def _delay(self, attempt: int, response: httpx2.Response | None) -> float:
        retry_after = response.headers.get("Retry-After") if response is not None else None
        if retry_after is not None and retry_after.isdigit():
            return min(float(retry_after), self._max_backoff)
        return min(self._backoff_base * 2.0 ** (attempt - 1), self._max_backoff)

    async def _get(self, url: httpx2.URL, label: str, params: dict[str, str] | None = None) -> Any:
        """GET with retries; returns parsed JSON. ``label`` names the request in errors."""
        status: int | None = None
        for attempt in range(1, self._max_attempts + 1):
            response: httpx2.Response | None = None
            try:
                response = await self._client.get(url, params=params)
            except httpx2.TransportError:
                status = None
            else:
                status = response.status_code
                if status in _NOT_FOUND_STATUSES:
                    raise ResourceNotFoundError(f"{label}: not found (HTTP {status})")
                if status < 300:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise FhirRequestError(
                            f"{label}: response is not JSON", status=status, transient=False
                        ) from exc
                if status not in _TRANSIENT_STATUSES:
                    raise FhirRequestError(
                        f"{label}: failed with HTTP {status}", status=status, transient=False
                    )
            if attempt < self._max_attempts:
                await self._sleep(self._delay(attempt, response))
        cause = f"HTTP {status}" if status is not None else "a network error or timeout"
        raise FhirRequestError(
            f"{label}: gave up after {self._max_attempts} attempts ({cause})",
            status=status,
            transient=True,
        )

    async def read_patient(self, patient_id: str) -> RawResource:
        validate_patient_id(patient_id)
        resource = await self._get(self._url(f"Patient/{patient_id}"), "read Patient")
        if not isinstance(resource, dict) or resource.get("resourceType") != "Patient":
            raise FhirRequestError("read Patient: response is not a Patient", transient=False)
        return resource

    async def search(
        self,
        resource_type: SearchType,
        patient_id: str,
        *,
        since: date | None = None,
        updated_since: datetime | None = None,
    ) -> SearchResult:
        validate_patient_id(patient_id)
        if resource_type not in DATE_SEARCH:
            raise ValueError(f"unsupported search type {resource_type!r}")
        params: dict[str, str] = {"patient": patient_id, "_count": str(self._page_size)}
        if since is not None:
            params[DATE_SEARCH[resource_type][0]] = f"ge{since.isoformat()}"
        if updated_since is not None:
            params["_lastUpdated"] = f"ge{updated_since.isoformat()}"
        if resource_type in MEDICATION_TYPES:
            params["_include"] = f"{resource_type}:medication"

        label = f"search {resource_type}"
        results: dict[tuple[str, str], RawResource] = {}
        without_id: list[RawResource] = []
        warnings: list[SearchWarning] = []
        url: httpx2.URL | None = self._url(resource_type)
        page_params: dict[str, str] | None = params
        pages = 0
        while url is not None:
            pages += 1
            if pages > self._max_pages:
                raise FhirRequestError(
                    f"{label}: stopped after {self._max_pages} pages", transient=False
                )
            bundle = await self._get(url, label, page_params)
            if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
                raise FhirRequestError(f"{label}: response is not a Bundle", transient=False)
            for entry in bundle.get("entry") or []:
                resource = entry.get("resource") or {}
                kind = resource.get("resourceType")
                if kind == "OperationOutcome":
                    warnings.extend(_warnings(resource))
                elif kind == resource_type and not resource.get("id"):
                    without_id.append(resource)  # reported as skipped by normalization
                elif kind in (resource_type, "Medication") and resource.get("id"):
                    results[(kind, resource["id"])] = resource
            url = self._next_link(bundle, label)
            page_params = None
        return SearchResult(resources=list(results.values()) + without_id, warnings=tuple(warnings))

    def _next_link(self, bundle: dict[str, Any], label: str) -> httpx2.URL | None:
        for link in bundle.get("link") or []:
            if link.get("relation") == "next" and link.get("url"):
                url = httpx2.URL(link["url"])
                if not self._same_origin(url):
                    raise FhirRequestError(
                        f"{label}: refusing to follow a next link to another origin",
                        transient=False,
                    )
                return url
        return None


def _issue_code(raw: Any) -> str:
    """A FHIR issue-type token, or "unknown": server text is never passed on."""
    return raw if isinstance(raw, str) and _ISSUE_CODE.fullmatch(raw) else "unknown"


def _warnings(outcome: dict[str, Any]) -> list[SearchWarning]:
    return [
        SearchWarning(severity=issue["severity"], code=_issue_code(issue.get("code")))
        for issue in outcome.get("issue") or []
        if isinstance(issue, dict) and issue.get("severity") in WARNING_SEVERITIES
    ]
