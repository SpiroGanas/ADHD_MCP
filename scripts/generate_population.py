"""Generate a bulk synthetic population for volume and performance tests.

Usage: uv run python scripts/generate_population.py [--count N] [--seed S] [--out DIR]

Deterministic for a given seed. Output is built on demand into ``build/`` (git-ignored) and
is not committed. The data is for volume only: hand-built personas carry the clinical
meaning. Codes are drawn from small fixed pools and are illustrative, not value-set content.
"""

import argparse
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.personas.builder import PersonaBuilder  # noqa: E402

START = date(2018, 1, 1)
END = date(2026, 6, 14)

CONDITIONS = [
    ("I10", "Essential (primary) hypertension", 0.25),
    ("E11.9", "Type 2 diabetes mellitus without complications", 0.10),
    ("J45.909", "Unspecified asthma, uncomplicated", 0.08),
    ("M54.50", "Low back pain, unspecified", 0.20),
    ("F32.9", "Major depressive disorder, single episode, unspecified", 0.12),
    ("F41.1", "Generalized anxiety disorder", 0.08),
    ("F43.10", "Post-traumatic stress disorder, unspecified", 0.07),
    ("F10.10", "Alcohol abuse, uncomplicated", 0.05),
    ("G47.00", "Insomnia, unspecified", 0.10),
    ("Z56.0", "Unemployment, unspecified", 0.04),
    ("Z59.00", "Homelessness unspecified", 0.02),
]
INJURIES = [
    ("S93.401A", "Sprain of unspecified ligament of right ankle"),
    ("S52.501A", "Unspecified fracture of the lower end of right radius"),
    ("S01.81XA", "Laceration without foreign body of other part of head"),
]
MEDICATIONS = [
    ("29046", "lisinopril"),
    ("6809", "metformin"),
    ("36437", "sertraline"),
    ("4493", "fluoxetine"),
    ("10689", "trazodone"),
]
SCREENS = [("55758-7", "PHQ-2 total score", 6), ("75626-2", "AUDIT-C total score", 12)]


def _day(rng: random.Random) -> date:
    return START + timedelta(days=rng.randrange((END - START).days))


def _patient(index: int, rng: random.Random) -> dict[str, Any]:
    gender = rng.choice(["male", "female", "female", "male", "other"])
    birth = date(rng.randint(1950, 2004), rng.randint(1, 12), rng.randint(1, 28))
    p = PersonaBuilder(
        f"g{index:05d}", gender=gender, birth_date=birth.isoformat(), number=10_000 + index
    )
    for _ in range(rng.randint(1, 8)):
        when = _day(rng)
        p.encounter("AMB", f"{when}T09:00:00Z", f"{when}T09:30:00Z")
    for code, display, probability in CONDITIONS:
        if rng.random() < probability:
            p.condition(code, display, recorded=_day(rng).isoformat())
    for _ in range(rng.choices([0, 1, 2, 3], weights=[70, 20, 7, 3])[0]):
        when = _day(rng)
        encounter = p.encounter("EMER", f"{when}T18:00:00Z", f"{when}T22:00:00Z")
        code, display = rng.choice(INJURIES)
        p.condition(
            code,
            display,
            recorded=when.isoformat(),
            encounter=encounter,
            category="encounter-diagnosis",
        )
    for code, name in MEDICATIONS:
        if rng.random() < 0.12:
            when = _day(rng)
            request = p.medication_request(code, name, when.isoformat(), days=30)
            p.medication_dispense(request, code, name, when.isoformat(), days=30)
    for code, display, maximum in SCREENS:
        if rng.random() < 0.5:
            p.observation(code, display, f"{_day(rng)}T10:00:00Z", value=rng.randint(0, maximum))
    return p.bundle()


def generate(count: int, *, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)  # noqa: S311 - synthetic test data, not security
    return [_patient(i, rng) for i in range(1, count + 1)]


def write_population(out: Path, *, count: int, seed: int) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for bundle in generate(count, seed=seed):
        path = out / f"{bundle['id'].removesuffix('-bundle')}.json"
        path.write_text(json.dumps(bundle) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, default=ROOT / "build" / "population")
    args = parser.parse_args()
    paths = write_population(args.out, count=args.count, seed=args.seed)
    print(f"Wrote {len(paths)} synthetic patients to {args.out}")


if __name__ == "__main__":
    main()
