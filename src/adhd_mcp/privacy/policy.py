"""Sensitive-data policy.

``PrivacyPort`` sits between the FHIR source and the evidence assemblers. A resource in a
withheld category never reaches an assembler; one in a cited category is passed on and its
reference is noted in the request's ``PrivacyLedger``. ``redact_output`` then replaces the
code of any output entry resting on a restricted resource with ``restricted``. Every output
says, per category, how many records were withheld or restricted.
"""

import tomllib
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from adhd_mcp.fhir.codes import Coding, normalize_coding
from adhd_mcp.fhir.normalize import normalize
from adhd_mcp.fhir.port import FhirReadPort, RawResource, SearchResult, SearchType
from adhd_mcp.fhir.reader import record_codes
from adhd_mcp.models.domain import PrivacyCount, PrivacyNote
from adhd_mcp.terminology import ValueSet, load_value_set

Action = Literal["allow", "cite", "withhold"]
RESTRICTED = "restricted"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Label(_Frozen):
    system: str
    code: str


class Category(_Frozen):
    id: str
    title: str
    value_sets: tuple[str, ...]
    labels: tuple[Label, ...]
    #: Whether outputs may name this category. False for categories no output or rule
    #: uses: naming them would reveal only that such a record exists.
    disclose: bool


class PolicyFile(_Frozen):
    id: str
    version: str
    actions: dict[str, Action]
    categories: tuple[Category, ...]


@dataclass(frozen=True)
class PrivacyPolicy:
    id: str
    version: str
    categories: tuple[Category, ...]
    actions: dict[str, Action]
    value_sets: dict[str, tuple[ValueSet, ...]]

    @property
    def label(self) -> str:
        return f"{self.id} {self.version}"

    def classify(self, raw: RawResource) -> set[str]:
        """Categories a raw resource belongs to, by security label or by code."""
        labels = {
            (c.system, c.code)
            for c in (normalize_coding(s) for s in (raw.get("meta") or {}).get("security") or [])
            if c is not None
        }
        found = {
            cat.id
            for cat in self.categories
            if any((label.system, label.code) in labels for label in cat.labels)
        }
        record = None
        try:
            record = normalize(raw)
        except Exception:
            record = None
        codes: tuple[Coding, ...] = record_codes(record) if record is not None else ()
        if record is not None:
            codes += getattr(record, "reason_codes", ())
        for cat in self.categories:
            if any(vs.matching_codings(codes) for vs in self.value_sets[cat.id]):
                found.add(cat.id)
        return found

    def action(self, category: str) -> Action:
        return self.actions.get(category, "cite")

    def disclosed(self, category: str) -> bool:
        return any(c.disclose for c in self.categories if c.id == category)


def parse_privacy_policy(text: str) -> PrivacyPolicy:
    data = PolicyFile.model_validate(tomllib.loads(text))
    ids = {c.id for c in data.categories}
    unknown = set(data.actions) - ids
    if unknown:
        raise ValueError(f"policy names unknown categories: {sorted(unknown)}")
    return PrivacyPolicy(
        id=data.id,
        version=data.version,
        categories=data.categories,
        actions={c: data.actions.get(c, "cite") for c in sorted(ids)},
        value_sets={c.id: tuple(load_value_set(v) for v in c.value_sets) for c in data.categories},
    )


def load_privacy_policy(path: Path | None = None) -> PrivacyPolicy:
    """The packaged default policy, or a site's own policy file."""
    if path is not None:
        return parse_privacy_policy(path.read_text(encoding="utf-8"))
    return parse_privacy_policy(
        files("adhd_mcp.data").joinpath("privacy.toml").read_text(encoding="utf-8")
    )


def with_actions(policy: PrivacyPolicy, actions: dict[str, Action]) -> PrivacyPolicy:
    return PrivacyPolicy(
        id=policy.id,
        version=policy.version,
        categories=policy.categories,
        actions=policy.actions | actions,
        value_sets=policy.value_sets,
    )


@dataclass
class PrivacyLedger:
    """What the policy did during one request."""

    withheld: Counter[str] = field(default_factory=Counter)
    restricted: Counter[str] = field(default_factory=Counter)
    restricted_refs: set[tuple[str, str]] = field(default_factory=set)
    #: Resource types that lost records to a withhold policy (disclosed categories only).
    withheld_types: set[str] = field(default_factory=set)
    _seen: set[tuple[str, ...]] = field(default_factory=set)

    def note(self, policy: PrivacyPolicy) -> PrivacyNote:
        """Only disclosed categories are named (see ``Category.disclose``)."""

        def counts(counter: Counter[str]) -> list[PrivacyCount]:
            return [
                PrivacyCount(category=c, records=n)
                for c, n in sorted(counter.items())
                if policy.disclosed(c)
            ]

        return PrivacyNote(
            policy=policy.label, withheld=counts(self.withheld), restricted=counts(self.restricted)
        )

    def count(self, kind: str, category: str, key: tuple[str, str]) -> None:
        # The same resource can be read twice in one request (several assemblers).
        if (kind, category, *key) not in self._seen:
            self._seen.add((kind, category, *key))
            (self.withheld if kind == "withheld" else self.restricted)[category] += 1


class PrivacyPort:
    """A read-only port that applies the policy to every resource it returns."""

    def __init__(self, inner: FhirReadPort, policy: PrivacyPolicy, ledger: PrivacyLedger) -> None:
        self._inner = inner
        self._policy = policy
        self.ledger = ledger

    async def read_patient(self, patient_id: str) -> RawResource:
        return await self._inner.read_patient(patient_id)

    async def search(
        self,
        resource_type: SearchType,
        patient_id: str,
        *,
        since: date | None = None,
        updated_since: datetime | None = None,
    ) -> SearchResult:
        found = await self._inner.search(
            resource_type, patient_id, since=since, updated_since=updated_since
        )
        kept: list[RawResource] = []
        for raw in found.resources:
            key = (str(raw.get("resourceType")), str(raw.get("id")))
            categories = self._policy.classify(raw)
            actions = {c: self._policy.action(c) for c in categories}
            withheld = sorted(c for c, a in actions.items() if a == "withhold")
            if withheld:
                for c in withheld:
                    self.ledger.count("withheld", c, key)
                    if self._policy.disclosed(c):
                        self.ledger.withheld_types.add(key[0])
                continue
            for c in sorted(c for c, a in actions.items() if a == "cite"):
                self.ledger.count("restricted", c, key)
                self.ledger.restricted_refs.add(key)
            kept.append(raw)
        return SearchResult(resources=kept, warnings=found.warnings)


def _restricted(refs: Any, restricted: set[tuple[str, str]]) -> bool:
    return any(
        isinstance(r, dict) and (r.get("resource_type"), r.get("id")) in restricted for r in refs
    )


def redact_output(value: Any, restricted: set[tuple[str, str]]) -> Any:
    """Replace the code of every entry that rests on a restricted resource. References,
    dates and the family or signal the entry belongs to are kept."""
    if isinstance(value, list):
        return [redact_output(v, restricted) for v in value]
    if not isinstance(value, dict):
        return value
    out = {k: redact_output(v, restricted) for k, v in value.items()}
    if _restricted(out.get("references") or [], restricted):
        if isinstance(out.get("code"), dict):
            out["code"] = {"system": None, "code": RESTRICTED, "display": None}
        if isinstance(out.get("answer"), dict):
            out["answer"] = {"system": None, "code": RESTRICTED, "display": None}
        if isinstance(out.get("ingredient"), dict):
            out["ingredient"] = {"rxcui": RESTRICTED, "name": RESTRICTED}
    return out
