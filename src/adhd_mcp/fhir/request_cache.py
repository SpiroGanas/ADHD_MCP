"""A read-only port wrapper that caches answers for the lifetime of one request.

``assess_referral_need`` runs several evidence assemblers that read the same categories;
wrapping the port for that one request means each distinct query reaches the FHIR server
once, including concurrent identical queries. Nothing is shared between requests, so no
patient data outlives the call. Failures are not cached.
"""

import asyncio
import copy
from datetime import date, datetime
from typing import Any

from adhd_mcp.fhir.port import FhirReadPort, RawResource, SearchResult, SearchType


class RequestCachedPort:
    def __init__(self, inner: FhirReadPort) -> None:
        self._inner = inner
        self._tasks: dict[tuple[Any, ...], asyncio.Task[Any]] = {}

    async def _once(self, key: tuple[Any, ...], make: Any) -> Any:
        existing = self._tasks.get(key)
        task: asyncio.Task[Any] = existing or asyncio.ensure_future(make())
        self._tasks[key] = task
        try:
            result = await asyncio.shield(task)
        except BaseException:
            if self._tasks.get(key) is task and task.done():
                del self._tasks[key]
            raise
        return copy.deepcopy(result)

    async def read_patient(self, patient_id: str) -> RawResource:
        result: RawResource = await self._once(
            ("Patient", patient_id), lambda: self._inner.read_patient(patient_id)
        )
        return result

    async def search(
        self,
        resource_type: SearchType,
        patient_id: str,
        *,
        since: date | None = None,
        updated_since: datetime | None = None,
    ) -> SearchResult:
        key = ("search", resource_type, patient_id, since, updated_since)
        result: SearchResult = await self._once(
            key,
            lambda: self._inner.search(
                resource_type, patient_id, since=since, updated_since=updated_since
            ),
        )
        return result
