"""The persona catalog: hand-built synthetic patients. Narratives and expected outcomes are
in ``catalog.toml``. All dates are chosen relative to the catalog's as-of date, 2026-06-15.

RxNorm codes and local codes in these fixtures are illustrative test data, not verified
value-set content.
"""

from collections.abc import Callable

from tests.personas.builder import LOINC, PersonaBuilder, Resource

PHQ9_QUESTIONNAIRE = "urn:adhd-mcp:synthetic-questionnaire:phq-9"


def _phq9_panel(p: PersonaBuilder, when: str, item9: int, total: int) -> None:
    item = p.observation("44260-8", "PHQ-9 item 9", when, value=item9)
    score = p.observation("44261-6", "PHQ-9 total score", when, value=total)
    p.observation("44249-1", "PHQ-9 panel", when, members=(item, score))


def p01() -> PersonaBuilder:
    """Clear ADHD-signal case."""
    p = PersonaBuilder("p01", gender="male", birth_date="1992-02-11")
    e1 = p.encounter("EMER", "2024-09-03T22:10:00Z", "2024-09-04T02:00:00Z")
    p.condition(
        "S62.302A",
        "Fracture of metacarpal bone",
        recorded="2024-09-03",
        encounter=e1,
        category="encounter-diagnosis",
    )
    p.condition(
        "W01.0XXA",
        "Fall from slipping, tripping",
        recorded="2024-09-03",
        encounter=e1,
        category="encounter-diagnosis",
    )
    e2 = p.encounter("EMER", "2025-11-20T17:00:00Z", "2025-11-20T21:30:00Z")
    p.condition(
        "V43.52XA",
        "Car driver injured in collision with car in traffic accident",
        recorded="2025-11-20",
        encounter=e2,
        category="encounter-diagnosis",
    )
    p.condition(
        "S13.4XXA",
        "Sprain of ligaments of cervical spine",
        recorded="2025-11-20",
        encounter=e2,
        category="encounter-diagnosis",
    )
    e3 = p.encounter("EMER", "2026-03-02T09:00:00Z", "2026-03-02T12:00:00Z")
    p.condition(
        "S61.411A",
        "Laceration of right hand",
        recorded="2026-03-02",
        encounter=e3,
        category="encounter-diagnosis",
    )
    p.condition(
        "W26.0XXA",
        "Contact with knife",
        recorded="2026-03-02",
        encounter=e3,
        category="encounter-diagnosis",
    )
    p.condition(
        "F15.10", "Other stimulant abuse, uncomplicated", onset="2025-03", recorded="2025-03-02"
    )
    p.condition("F10.10", "Alcohol abuse, uncomplicated", onset="2024", recorded="2024-08-14")
    p.condition("G47.00", "Insomnia, unspecified", recorded="2025-06-01")
    p.condition("Z56.0", "Unemployment, unspecified", recorded="2025-12-01")
    _phq9_panel(p, "2026-02-01T10:00:00Z", item9=0, total=8)
    return p


def p02() -> PersonaBuilder:
    """Female presentation: recurrent depression, anxiety, many antidepressant switches."""
    p = PersonaBuilder("p02", gender="female", birth_date="1997-09-30")
    p.condition(
        "F33.1",
        "Major depressive disorder, recurrent, moderate",
        onset="2018",
        recorded="2019-01-15",
    )
    p.condition("F41.1", "Generalized anxiety disorder", onset="2019-05", recorded="2019-05-20")
    p.condition("G47.00", "Insomnia, unspecified", recorded="2022-03-03")
    p.condition("R41.840", "Attention and concentration deficit", recorded="2025-10-10")
    drugs = [
        ("36437", "sertraline", "2019-02-01"),
        ("321988", "escitalopram", "2020-06-15"),
        ("42347", "bupropion", "2021-11-02"),
        ("39786", "venlafaxine", "2023-04-20"),
        ("4493", "fluoxetine", "2025-01-12"),
    ]
    for code, name, when in drugs:
        request = p.medication_request(code, name, when, days=90)
        p.medication_dispense(request, code, name, when, days=90)
    p.questionnaire_response(
        PHQ9_QUESTIONNAIRE,
        "2026-01-20",
        {"1": 2, "2": 2, "3": 3, "4": 2, "5": 1, "6": 1, "7": 2, "8": 0, "9": 0, "total": 13},
    )
    p.observation("75626-2", "AUDIT-C total score", "2026-01-20T10:00:00Z", value=3)
    return p


def p03() -> PersonaBuilder:
    """Safety gate case: recent ideation, positive item 9, high C-SSRS, recent discharge."""
    p = PersonaBuilder("p03", gender="male", birth_date="1985-04-02")
    admission = p.encounter(
        "IMP",
        "2026-03-30T15:00:00Z",
        "2026-04-10T11:00:00Z",
        service="psychiatric-inpatient",
        reasons=(("R45.851", "Suicidal ideations"),),
    )
    p.condition(
        "R45.851",
        "Suicidal ideations",
        recorded="2026-03-30",
        encounter=admission,
        category="encounter-diagnosis",
    )
    p.condition(
        "F15.20", "Other stimulant dependence, uncomplicated", onset="2023", recorded="2023-07-07"
    )
    _phq9_panel(p, "2026-05-20T09:30:00Z", item9=2, total=19)
    risk = p.observation(
        "93374-7", "Suicide risk level", "2026-05-20T09:45:00Z", value_code=("LA9193-9", "High")
    )
    p.observation("93373-9", "C-SSRS screener", "2026-05-20T09:45:00Z", members=(risk,))
    p.flag("high-risk-for-suicide", "2026-04-10")
    return p


def p04() -> PersonaBuilder:
    """Already diagnosed: an ADHD code and stimulant treatment."""
    p = PersonaBuilder("p04", gender="male", birth_date="1990-12-24")
    p.condition(
        "F90.0", "ADHD, predominantly inattentive type", onset="2021", recorded="2021-09-09"
    )
    p.condition("F10.10", "Alcohol abuse, uncomplicated", recorded="2020-02-02")
    request = p.medication_request("6901", "methylphenidate", "2026-05-01", reason=("F90.0", ""))
    p.medication_dispense(request, "6901", "methylphenidate", "2026-05-02")
    return p


def p05() -> PersonaBuilder:
    """TBI look-alike: concussion, history of TBI, attention complaints, insomnia."""
    p = PersonaBuilder("p05", gender="male", birth_date="1988-07-19")
    e1 = p.encounter("EMER", "2024-05-11T13:00:00Z", "2024-05-11T19:00:00Z")
    p.condition(
        "S06.0X1A",
        "Concussion with loss of consciousness of 30 minutes or less",
        recorded="2024-05-11",
        encounter=e1,
        category="encounter-diagnosis",
    )
    p.condition("Z87.820", "Personal history of traumatic brain injury", recorded="2025-01-15")
    p.condition("R41.840", "Attention and concentration deficit", recorded="2025-01-15")
    p.condition("G47.00", "Insomnia, unspecified", recorded="2025-02-20")
    return p


def p06() -> PersonaBuilder:
    """Narcolepsy treated with a stimulant: not an ADHD stimulant signal."""
    p = PersonaBuilder("p06", gender="female", birth_date="1994-03-08")
    p.condition("G47.419", "Narcolepsy without cataplexy", onset="2020", recorded="2020-10-10")
    for when in ("2026-01-05", "2026-02-04", "2026-03-06"):
        request = p.medication_request("725", "amphetamine", when, reason=("G47.419", ""))
        p.medication_dispense(request, "725", "amphetamine", when)
    return p


def p07() -> PersonaBuilder:
    """Empty record: a patient and nothing else."""
    return PersonaBuilder("p07", gender="unknown", birth_date="1980")


def p08() -> PersonaBuilder:
    """Sparse record: one primary care visit."""
    p = PersonaBuilder("p08", gender="female", birth_date="1979-05")
    encounter = p.encounter("AMB", "2025-08-01T09:00:00Z", "2025-08-01T09:30:00Z")
    p.condition(
        "I10",
        "Essential (primary) hypertension",
        recorded="2025-08-01",
        encounter=encounter,
        category="encounter-diagnosis",
    )
    return p


def p09() -> PersonaBuilder:
    """Conflicting data: duplicates, entered-in-error, refuted ADHD, an old cancelled referral."""
    p = PersonaBuilder("p09", gender="male", birth_date="1983-11-01")
    e1 = p.encounter("AMB", "2023-02-01T10:00:00Z", "2023-02-01T10:30:00Z")
    e2 = p.encounter("AMB", "2024-02-01T10:00:00Z", "2024-02-01T10:30:00Z")
    p.condition(
        "F43.10",
        "Post-traumatic stress disorder, unspecified",
        recorded="2023-02-01",
        encounter=e1,
        category="encounter-diagnosis",
    )
    p.condition(
        "F43.10",
        "Post-traumatic stress disorder, unspecified",
        recorded="2024-02-01",
        encounter=e2,
        category="encounter-diagnosis",
    )
    p.condition(
        "F15.10",
        "Other stimulant abuse, uncomplicated",
        recorded="2024-02-01",
        verification="entered-in-error",
    )
    p.condition(
        "F90.9",
        "ADHD, unspecified type",
        recorded="2022-06-01",
        verification="refuted",
        clinical="inactive",
    )
    p.condition(
        "F32.9",
        "Major depressive disorder, single episode, unspecified",
        onset="2019",
        recorded="2019-03-03",
        clinical="resolved",
    )
    p.observation(
        "44261-6", "PHQ-9 total score", "2024-02-01T10:10:00Z", value=27, status="entered-in-error"
    )
    p.observation("44261-6", "PHQ-9 total score", "2024-02-01T10:12:00Z", value=7)
    p.service_request("adhd-evaluation-referral", "2019-04-01", status="revoked", reason="R41.840")
    return p


def p10() -> PersonaBuilder:
    """Healthy control: routine visits, negative screens."""
    p = PersonaBuilder("p10", gender="female", birth_date="1981-01-17")
    for year in ("2024", "2025", "2026"):
        p.encounter("AMB", f"{year}-04-10T09:00:00Z", f"{year}-04-10T09:20:00Z")
    p.observation("55758-7", "PHQ-2 total score", "2026-04-10T09:05:00Z", value=0)
    p.observation("75626-2", "AUDIT-C total score", "2026-04-10T09:06:00Z", value=1)
    return p


def p11() -> PersonaBuilder:
    """Two high-weight classes and no modifiers: stimulant dependence and a crash as driver."""
    p = PersonaBuilder("p11", gender="male", birth_date="1995-08-21")
    visit = p.encounter("EMER", "2024-08-10T18:00:00Z", "2024-08-10T23:00:00Z")
    p.condition(
        "V43.52XA",
        "Car driver injured in collision with car in traffic accident",
        recorded="2024-08-10",
        encounter=visit,
        category="encounter-diagnosis",
    )
    p.condition(
        "S80.01XA",
        "Contusion of right knee",
        recorded="2024-08-10",
        encounter=visit,
        category="encounter-diagnosis",
    )
    p.condition(
        "F15.20",
        "Other stimulant dependence, uncomplicated",
        onset="2025-01",
        recorded="2025-02-01",
    )
    return p


def p12() -> PersonaBuilder:
    """Narrow miss: one high-weight signal (alcohol) with only one modifier (PTSD)."""
    p = PersonaBuilder("p12", gender="female", birth_date="1988-02-14")
    p.condition("F10.20", "Alcohol dependence, uncomplicated", recorded="2025-04-01")
    p.condition("F43.10", "Post-traumatic stress disorder, unspecified", recorded="2024-01-10")
    p.encounter("AMB", "2025-04-01T09:00:00Z", "2025-04-01T09:40:00Z")
    return p


def p13() -> PersonaBuilder:
    """Window miss: the crash as driver is one day outside the 1095-day window."""
    p = PersonaBuilder("p13", gender="male", birth_date="1984-10-03")
    visit = p.encounter("EMER", "2023-06-15T20:00:00Z", "2023-06-16T01:00:00Z")
    p.condition(
        "V43.52XA",
        "Car driver injured in collision with car in traffic accident",
        recorded="2023-06-15",
        encounter=visit,
        category="encounter-diagnosis",
    )
    p.condition("F10.10", "Alcohol abuse, uncomplicated", recorded="2025-09-01")
    p.condition("Z65.3", "Problems related to other legal circumstances", recorded="2025-10-01")
    return p


def p14() -> PersonaBuilder:
    """Female presentation that triggers: alcohol involvement with many modifiers."""
    p = PersonaBuilder("p14", gender="female", birth_date="1993-12-01")
    visit = p.encounter(
        "EMER",
        "2025-12-20T01:00:00Z",
        "2025-12-20T06:00:00Z",
        reasons=(("Y90.2", "Blood alcohol level of 40-59 mg/100 ml"),),
    )
    p.condition(
        "Y90.2",
        "Blood alcohol level of 40-59 mg/100 ml",
        recorded="2025-12-20",
        encounter=visit,
        category="encounter-diagnosis",
    )
    p.condition("F60.3", "Borderline personality disorder", onset="2021-05", recorded="2021-05-20")
    p.condition("F63.81", "Intermittent explosive disorder", recorded="2024-07-15")
    p.condition("F12.20", "Cannabis dependence, uncomplicated", recorded="2024-03-03")
    p.condition(
        "Z59.811", "Housing instability, housed, with risk of homelessness", recorded="2025-11-05"
    )
    p.condition(
        "Z81.8", "Family history of other mental and behavioral disorders", recorded="2020-01-10"
    )
    drugs = [
        ("36437", "sertraline", "2023-09-01"),
        ("321988", "escitalopram", "2024-03-01"),
        ("42347", "bupropion", "2024-10-01"),
        ("72625", "duloxetine", "2025-06-01"),
    ]
    for code, name, when in drugs:
        request = p.medication_request(code, name, when, days=90)
        p.medication_dispense(request, code, name, when, days=90)
    return p


PERSONAS: dict[str, Callable[[], PersonaBuilder]] = {
    "p01": p01,
    "p02": p02,
    "p03": p03,
    "p04": p04,
    "p05": p05,
    "p06": p06,
    "p07": p07,
    "p08": p08,
    "p09": p09,
    "p10": p10,
    "p11": p11,
    "p12": p12,
    "p13": p13,
    "p14": p14,
}


def build_bundles() -> dict[str, Resource]:
    return {key: factory().bundle() for key, factory in PERSONAS.items()}


__all__ = ["LOINC", "PERSONAS", "PHQ9_QUESTIONNAIRE", "build_bundles"]
