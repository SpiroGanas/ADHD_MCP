"""An in-process stand-in for a FHIR R4 server, served through ``httpx2.MockTransport``.

It answers ``GET [base]/Patient/{id}`` and ``GET [base]/{type}?patient=...`` with paging,
date and ``_lastUpdated`` filters and Medication includes, backed by a fixture adapter. It
records every request so tests can prove the client never writes. Fault injection is by
``fail_next``: a list of status codes (or exceptions) returned before normal handling.
"""

import asyncio
import contextlib
import json
import math
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

import httpx2

from adhd_mcp.fhir.errors import ResourceNotFoundError
from adhd_mcp.fhir.fixture_adapter import FixtureFhirAdapter
from adhd_mcp.fhir.port import RawResource, SearchType
from adhd_mcp.fhir.search import DATE_SEARCH

BASE = "http://fhir.test/r4"


class FakeFhirServer:
    def __init__(
        self, resources: Iterable[RawResource], *, page_size: int = 3, base: str = BASE
    ) -> None:
        self.base = base
        self.store = FixtureFhirAdapter(resources)
        self.page_size = page_size
        self.requests: list[httpx2.Request] = []
        #: JSON bodies of the answers, in order (non-JSON answers are left out).
        self.responses: list[Any] = []
        self.fail_next: list[int | Exception | httpx2.Response] = []
        self.next_link_base = base

    def transport(self) -> httpx2.MockTransport:
        return httpx2.MockTransport(self.handle)

    def _bundle(self, entries: list[RawResource], next_url: str | None) -> dict[str, Any]:
        links = [{"relation": "next", "url": next_url}] if next_url else []
        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": links,
            "entry": [{"resource": r, "search": {"mode": "match"}} for r in entries],
        }

    async def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        response = await self.respond(request)
        with contextlib.suppress(ValueError):
            self.responses.append(json.loads(response.content))
        return response

    async def respond(self, request: httpx2.Request) -> httpx2.Response:  # noqa: PLR0911
        """Answer a request without recording it."""
        if self.fail_next:
            failure = self.fail_next.pop(0)
            if isinstance(failure, Exception):
                raise failure
            if isinstance(failure, httpx2.Response):
                return failure
            return httpx2.Response(failure, text="server detail that must not leak")
        if request.method != "GET":
            return httpx2.Response(405)
        path = request.url.path.removeprefix(httpx2.URL(self.base).path).strip("/").split("/")
        if len(path) == 2 and path[0] == "Patient":
            try:
                return httpx2.Response(200, json=await self.store.read_patient(path[1]))
            except ResourceNotFoundError:
                return httpx2.Response(404, json={"resourceType": "OperationOutcome"})
        if len(path) == 1 and path[0] in DATE_SEARCH:
            return await self._search(path[0], request.url.params)  # type: ignore[arg-type]
        return httpx2.Response(400)

    async def _search(
        self, resource_type: SearchType, params: httpx2.QueryParams
    ) -> httpx2.Response:
        date_param = DATE_SEARCH[resource_type][0]
        since = params.get(date_param)
        updated = params.get("_lastUpdated")
        found = await self.store.search(
            resource_type,
            params["patient"],
            since=date.fromisoformat(since.removeprefix("ge")) if since else None,
            updated_since=datetime.fromisoformat(updated.removeprefix("ge")) if updated else None,
            categories=tuple(params["category"].split(",")) if params.get("category") else (),
            codes=tuple((None, c) for c in params["combo-code"].split(","))
            if params.get("combo-code")
            else (),
        )
        results = found.resources
        count = int(params.get("_count", self.page_size))
        offset = int(params.get("_offset", 0))
        page = results[offset : offset + count]
        next_url = None
        if offset + count < len(results):
            query = dict(params) | {"_offset": str(offset + count), "_count": str(count)}
            next_url = str(httpx2.URL(f"{self.next_link_base}/{resource_type}", params=query))
        return httpx2.Response(200, json=self._bundle(page, next_url))

    def pages_for(self, total: int) -> int:
        return max(1, math.ceil(total / self.page_size))


async def no_sleep(_: float) -> None:
    await asyncio.sleep(0)
