"""Read-only, versioned reference material as MCP resources.

No patient data: the active ruleset and signal catalog, value sets, drug classes, instrument
metadata (codes and cutoffs with their verification status; no copyrighted item text), and
the intended-use statement.
"""

import json
from collections.abc import Callable
from importlib.resources import files
from typing import Any

from fastmcp import FastMCP

from adhd_mcp.conditions.base import ConditionPlugin
from adhd_mcp.terminology import load_value_set, packaged_value_set_ids
from adhd_mcp.terminology.drug_classes import load_drug_class, packaged_drug_class_ids
from adhd_mcp.terminology.instruments import load_instrument, packaged_instrument_ids
from adhd_mcp.tools.context import ToolContext

SCHEME = "adhd-mcp://"


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str)


def _condition_readers(plugin: ConditionPlugin) -> tuple[Callable[[], str], Callable[[], str]]:
    def ruleset() -> str:
        return _json(plugin.ruleset.model_dump(mode="json"))

    def catalog() -> str:
        return _json(plugin.catalog.model_dump(mode="json"))

    return ruleset, catalog


def register(mcp: FastMCP, context: ToolContext) -> None:
    for condition_id in context.conditions.ids():
        plugin = context.conditions.get(condition_id)
        ruleset, catalog = _condition_readers(plugin)

        mcp.resource(
            f"{SCHEME}rulesets/{condition_id}",
            name=f"{condition_id}_ruleset",
            title=f"Active {plugin.title} referral ruleset",
            description=f"Ruleset {plugin.ruleset.label}: rules, exclusions and citations. "
            "Not clinically validated.",
            mime_type="application/json",
        )(ruleset)
        mcp.resource(
            f"{SCHEME}signal-catalogs/{condition_id}",
            name=f"{condition_id}_signal_catalog",
            title=f"{plugin.title} signal catalog",
            description=f"Signal catalog {plugin.catalog.id} {plugin.catalog.version}: each "
            "signal's weight, definition, window, supplying tool and evidence.",
            mime_type="application/json",
        )(catalog)

    @mcp.resource(
        f"{SCHEME}value-sets",
        name="value_sets",
        title="Value set index",
        description="Every packaged value set: id, version and title.",
        mime_type="application/json",
    )
    def value_sets() -> str:
        index = []
        for vs_id in packaged_value_set_ids():
            vs = load_value_set(vs_id, strict=False)
            index.append({"id": vs.id, "version": vs.version, "title": vs.title})
        return _json(index)

    @mcp.resource(
        SCHEME + "value-sets/{value_set_id}",
        name="value_set",
        title="Value set",
        description="One value set with every entry and its verification provenance.",
        mime_type="application/json",
    )
    def value_set(value_set_id: str) -> str:
        if value_set_id not in packaged_value_set_ids():
            raise ValueError("unknown value set")
        return _json(load_value_set(value_set_id, strict=False).model_dump(mode="json"))

    @mcp.resource(
        f"{SCHEME}drug-classes",
        name="drug_classes",
        title="Drug classes",
        description="RxNorm drug classes (ADR 0009): ingredients with provenance and the "
        "number of product codes each covers.",
        mime_type="application/json",
    )
    def drug_classes() -> str:
        out = []
        for class_id in packaged_drug_class_ids():
            dc = load_drug_class(class_id, strict=False)
            out.append(
                {
                    "id": dc.id,
                    "version": dc.version,
                    "title": dc.title,
                    "ingredients": [
                        i.model_dump(mode="json", exclude={"products"})
                        | {"product_codes": len(i.products)}
                        for i in dc.ingredients
                    ],
                }
            )
        return _json(out)

    @mcp.resource(
        f"{SCHEME}instruments",
        name="instruments",
        title="Screening instrument metadata",
        description="Instrument names, codes and cutoffs with verification status. No item "
        "text is included (some instruments are copyrighted).",
        mime_type="application/json",
    )
    def instruments() -> str:
        out = []
        for instrument_id in packaged_instrument_ids():
            data = load_instrument(instrument_id, strict=False).model_dump(mode="json")
            for code in data["codes"]:
                if code["role"] == "item":
                    # An item's code name can repeat the item's wording.
                    code["display"] = None
            out.append(data)
        return _json(out)

    @mcp.resource(
        f"{SCHEME}intended-use",
        name="intended_use",
        title="Intended use statement",
        description="What this server is for and not for. It never diagnoses.",
        mime_type="text/markdown",
    )
    def intended_use() -> str:
        return files("adhd_mcp.data").joinpath("intended_use.md").read_text(encoding="utf-8")
