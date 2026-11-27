"""Build and render the versioned ruleset evaluation report (Phase 7, item 2).

The report is tied to a ruleset version and to fingerprints of the clinical content and the
cohort it was computed from, so a stale report is detectable without re-running it
(``tests/evals/test_report.py``). Regenerate with ``scripts/evaluate_ruleset.py``.
"""

import hashlib
import json
from collections.abc import Sequence
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from adhd_mcp.conditions.adhd import adhd_plugin
from tests.evals import harness as h
from tests.evals.cohort import AS_OF, COHORT_VERSION, CohortPatient

HARNESS_VERSION = "1.0.0"
REPORT_DIR = Path(__file__).resolve().parents[2] / "docs" / "evaluation"

MIX = h.MIX

LIMITATIONS = [
    "The cohort is designed, not sampled: rates in it say nothing about real-world "
    "prevalence, sensitivity or specificity.",
    "The research profile of each archetype is the cohort designer's reading of the research "
    "report, not a diagnosis and not ground truth.",
    "Agreement with intended outcomes shows that the code applies ruleset 1.0.0 as written. "
    "It is not evidence of clinical accuracy.",
    "The ruleset is sex-blind and age-blind, so differences by sex or age band come only from "
    "the presentations the cohort assigns to them; the cohort assigns every archetype to "
    "every sex and age band equally.",
    "The sex-balance reweighting uses an illustrative presentation mix, not an estimate.",
    "Coded data only: free-text notes are not read, and a missing code is weak evidence of "
    "absence. Real records are messier than these.",
    "The ruleset is not clinically validated.",
]


def _content_files() -> list[Traversable]:
    data = files("adhd_mcp.data")
    chosen = [data / "adhd" / "ruleset.toml", data / "adhd" / "signal_catalog.toml"]
    for folder in ("value_sets", "drug_classes"):
        chosen += sorted(
            (f for f in (data / folder).iterdir() if f.name.endswith(".toml")),
            key=lambda f: f.name,
        )
    return chosen


def content_fingerprint() -> str:
    """sha256 over the ruleset, the signal catalog, the value sets and the drug classes."""
    digest = hashlib.sha256()
    for f in _content_files():
        digest.update(f.name.encode() + b"\0" + f.read_bytes() + b"\0")
    return digest.hexdigest()


def cohort_fingerprint(patients: Sequence[CohortPatient]) -> str:
    rows = [
        {
            "patient": p.patient_id,
            "archetype": p.archetype.id,
            "profile": p.archetype.profile,
            "style": p.archetype.style,
            "intended": [
                p.archetype.recommendation,
                sorted(p.archetype.signals),
                sorted(p.archetype.rules_fired),
                p.archetype.safety_gate,
            ],
            "sex": p.sex,
            "age_band": p.age_band,
            "resources": p.resources,
        }
        for p in patients
    ]
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def identity(patients: Sequence[CohortPatient]) -> dict[str, Any]:
    plugin = adhd_plugin()
    return {
        "harness_version": HARNESS_VERSION,
        "ruleset": plugin.ruleset.label,
        "catalog": f"{plugin.catalog.id} {plugin.catalog.version}",
        "content_sha256": content_fingerprint(),
        "cohort_version": COHORT_VERSION,
        "cohort_sha256": cohort_fingerprint(patients),
        "as_of": AS_OF.isoformat(),
    }


def build_report(
    patients: Sequence[CohortPatient],
    results: Sequence[h.PatientResult],
    sensitivity: dict[str, dict[str, Any]],
    options: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    style = h.suggestive_by_style(results)
    return {
        "title": "ADHD ruleset evaluation on the labelled synthetic cohort",
        "identity": identity(patients),
        "cohort": {
            "patients": len(patients),
            "archetypes": len({p.archetype.id for p in patients}),
            "by_sex": dict(sorted(_count(p.sex for p in patients).items())),
            "by_age_band": dict(sorted(_count(p.age_band for p in patients).items())),
        },
        "agreement": h.agreement(results),
        "recommendations": h.recommendation_counts(results),
        "by_sex": h.rates_by(results, lambda r: r.patient.sex),
        "by_age_band": h.rates_by(results, lambda r: r.patient.age_band),
        "drivers": h.drivers(results),
        "by_profile": h.by_profile(results),
        "suggestive_by_style": style,
        "suggestive_by_sex": h.suggestive_by_sex(results),
        "mix_assumption": MIX,
        "mixed_recall": h.mixed_recall(style, MIX),
        "archetypes": h.archetype_outcomes(results),
        "sensitivity": sensitivity,
        "options": options,
        "limitations": LIMITATIONS,
    }


def _count(values: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


# --- Markdown -------------------------------------------------------------------------------


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def _rate(r: dict[str, Any] | None) -> str:
    return "n/a" if r is None else f"{r['flagged']} of {r['total']} ({_pct(r['rate'])})"


def _counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{k} {v}" for k, v in counts.items()) or "none"


def _table(header: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return [*lines, ""]


def _variant_rows(variants: dict[str, dict[str, Any]]) -> list[list[Any]]:
    return [
        [
            v["description"],
            v["flagged"],
            _rate(v["suggestive"]),
            _rate(v["not_suggestive"]),
            " / ".join(f"{sex} {_pct(r)}" for sex, r in v["mixed_recall"].items()),
            _counts(v["newly_flagged"]),
            _counts(v["no_longer_flagged"]),
        ]
        for v in variants.values()
    ]


VARIANT_HEADER = (
    "Change",
    "Suggestions (of all)",
    "Suggestive flagged",
    "Not-suggestive flagged",
    "Suggestive flagged under the illustrative mix",
    "Newly flagged archetypes",
    "No longer flagged",
)


def render_markdown(report: dict[str, Any]) -> str:
    ident, agree = report["identity"], report["agreement"]
    out = [
        f"# {report['title']}",
        "",
        "Generated by `uv run python scripts/evaluate_ruleset.py`; do not edit by hand. "
        "The methods and the sex-balance discussion are in "
        "[sex_balance_review.md](sex_balance_review.md) and the "
        "[rule card](../clinical/rule_card_adhd_1.0.md).",
        "",
        "> **Results on a designed synthetic cohort show whether the software applies the "
        "rules as intended. They say nothing about real-world accuracy.** The ruleset is not "
        "clinically validated.",
        "",
    ]
    out += _table(
        ("Item", "Value"),
        [
            ("Ruleset", f"`{ident['ruleset']}`, catalog `{ident['catalog']}`"),
            ("Clinical content sha256", f"`{ident['content_sha256'][:16]}...`"),
            ("Cohort", f"version {ident['cohort_version']}, "
             f"sha256 `{ident['cohort_sha256'][:16]}...`"),
            ("As-of date", ident["as_of"]),
            ("Harness version", ident["harness_version"]),
        ],
    )  # fmt: skip
    cohort = report["cohort"]
    out += [
        "## Cohort",
        "",
        f"{cohort['patients']} synthetic patients: {cohort['archetypes']} archetypes "
        "(`tests/evals/cohort.py`), each built once for every sex and age band. By sex: "
        f"{_counts(cohort['by_sex'])}. By age band: {_counts(cohort['by_age_band'])}.",
        "",
        "## Agreement with intended outcomes",
        "",
        f"{agree['agree']} of {agree['patients']} patients match their archetype's intended "
        "recommendation, present signals, fired rules and safety gate status.",
        "",
    ]
    out += _table(("Field", "Patients matching"), [(k, v) for k, v in agree["by_field"].items()])
    if agree["mismatches"]:
        out += _table(
            ("Patient", "Archetype", "Field", "Intended", "Actual"),
            [list(m.values()) for m in agree["mismatches"]],
        )
    out += ["## Outcomes by archetype", ""]
    out += _table(
        ("Archetype", "Title", "Research profile", "Style", "Intended", "Outcomes"),
        [
            (k, a["title"], a["profile"], a["style"] or "", a["intended"],
             _counts(a["recommendations"]))
            for k, a in report["archetypes"].items()
        ],
    )  # fmt: skip
    out += ["## Recommendations by sex and age band", ""]
    out += [f"All patients: {_counts(report['recommendations'])}.", ""]
    out += _table(
        ("Group", "Referral suggested", "All outcomes"),
        [
            (g, _rate(r), _counts(r["recommendations"]))
            for g, r in (report["by_sex"] | report["by_age_band"]).items()
        ],
    )
    drivers = report["drivers"]
    out += [
        "## What drives the suggestions",
        "",
        f"Among the {drivers['flagged']} patients given a referral suggestion:",
        "",
    ]
    out += _table(("Signal", "Present in"), list(drivers["signals"].items()))
    out += _table(("Rule", "Fired for"), list(drivers["rules"].items()))
    out += ["## Research-profile groups", ""]
    out += _table(
        ("Group", "Referral suggested"),
        [(g, _rate(r)) for g, r in report["by_profile"].items()]
        + [(f"suggestive, {g}", _rate(r)) for g, r in report["suggestive_by_style"].items()]
        + [(f"suggestive, {g}", _rate(r)) for g, r in report["suggestive_by_sex"].items()],
    )
    mix = report["mix_assumption"]
    out += [
        "## Sex balance",
        "",
        "The ruleset is sex-blind and the cohort is balanced, so the suggestion rate is the same "
        "for women and men here by construction. What differs is how the rules treat the two "
        "presentation styles above. If each sex's suggestive presentations followed the "
        "illustrative mix below (an assumption, not an estimate), the share flagged would be:",
        "",
    ]
    out += _table(
        ("Sex", "Assumed mix", "Share of suggestive presentations flagged"),
        [
            (sex, ", ".join(f"{s} {w:.0%}" for s, w in mix[sex].items()), _pct(r))
            for sex, r in report["mixed_recall"].items()
        ],
    )
    out += [
        "## Threshold sensitivity",
        "",
        "Each row changes one threshold of ruleset 1.0.0 and re-runs the cohort.",
        "",
    ]
    out += _table(VARIANT_HEADER, _variant_rows(report["sensitivity"]))
    out += [
        "## Sex-balance options (measured, not adopted)",
        "",
        "Candidate changes for the project owner. None is part of ruleset 1.0.0; adopting one "
        "makes a new ruleset version with its own tests.",
        "",
    ]
    out += _table(VARIANT_HEADER, _variant_rows(report["options"]))
    out += ["## Limitations", ""]
    out += [f"- {item}" for item in report["limitations"]]
    return "\n".join(out) + "\n"


def report_paths(ruleset_version: str) -> tuple[Path, Path]:
    stem = f"adhd_ruleset_{ruleset_version}"
    return REPORT_DIR / f"{stem}.json", REPORT_DIR / f"{stem}.md"


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=False) + "\n"
