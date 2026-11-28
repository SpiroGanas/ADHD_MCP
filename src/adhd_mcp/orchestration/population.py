"""The intended population: adults alive at the as-of date (peer review 01, C3).

A record outside it gets ``outside_intended_population`` before any rule runs. Where the
record cannot rule out a younger age (a birth year only, or no birth date), it is treated as
outside: a suggestion meant for adults is never made on a guess.
"""

from datetime import date

from adhd_mcp.fhir.records import PatientRecord

#: Keys of the wording notes that say why (``data/wording.toml``, ``[notes]``).
UNDER_AGE = "population_under_age"
NO_BIRTH_DATE = "population_no_birth_date"
DECEASED = "population_deceased"


def _age(born: date, on: date) -> int:
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


def outside_population(patient: PatientRecord, as_of: date, min_age_years: int) -> str | None:
    """The note key saying why the record is outside the intended population, or ``None``."""
    if patient.deceased and (
        patient.deceased_date is None
        or patient.deceased_date.start is None
        or patient.deceased_date.start <= as_of
    ):
        return DECEASED
    birth = patient.birth_date
    latest_birth = birth.end if birth is not None else None
    if latest_birth is None:
        return NO_BIRTH_DATE
    if _age(latest_birth, as_of) < min_age_years:
        return UNDER_AGE
    return None
