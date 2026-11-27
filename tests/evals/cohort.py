"""The labelled synthetic cohort (Phase 7, item 1).

A designed cohort, not a sample: 23 hand-written archetypes, each built once for every
combination of sex (female, male) and age band (18-29, 30-44, 45-64, 65+), so 184 patients
balanced by sex and age. Codes and dates vary between the copies of an archetype (always
inside the same value sets and windows), so the copies are not identical.

Every archetype states, by hand and before any evaluation run:

* the intended outcome under ADHD ruleset 1.0.0 (recommendation, present signals, fired
  rules, safety gate status): what the code must do;
* a *research profile*: whether the record is the kind the research report describes as one
  where formal screening is worth considering (``suggestive``), a look-alike or control
  where it is not (``not_suggestive``), a boundary case built to sit just either side of a
  rule (``boundary``), or a case the ruleset does not decide (``not_applicable``: safety
  gate, already in care, empty record);
* for suggestive records, a *presentation style*: ``externalizing`` (injuries, crashes,
  substance use, legal problems) or ``internalizing`` (depression, anxiety, insomnia,
  attention complaints, antidepressant changes). The research report says women are more
  often first labelled depressed or anxious and that injury, crash and legal signals skew
  male.

The research profile is the cohort designer's reading of the research report. It is not a
diagnosis, not ground truth and not evidence of real-world accuracy: results on this cohort
show whether the code applies the rules as intended, and how the rules treat the designed
presentations. All dates are relative to the as-of date, 2026-06-15. Codes are synthetic
test content chosen from verified value sets; RxNorm codes are illustrative.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Literal

from tests.personas.builder import PersonaBuilder, Resource

AS_OF = date(2026, 6, 15)
SEXES = ("female", "male")
AGE_BANDS: dict[str, int] = {"18-29": 24, "30-44": 37, "45-64": 52, "65+": 71}
COHORT_VERSION = "1.0.0"

Profile = Literal["suggestive", "not_suggestive", "boundary", "not_applicable"]
Style = Literal["externalizing", "internalizing"]
Build = Callable[[PersonaBuilder, int], None]

CLEAR_LIMITED = "clear_limited_data"
CONSIDER = "consider_referral_for_formal_screening"
NO_REC = "no_recommendation"


def ago(days: int) -> str:
    return (AS_OF - timedelta(days=days)).isoformat()


def pick[T](options: list[T] | tuple[T, ...], variant: int) -> T:
    return options[variant % len(options)]


# --- building blocks ---------------------------------------------------------------------

ALCOHOL = [
    ("F10.10", "Alcohol abuse, uncomplicated"),
    ("F10.20", "Alcohol dependence, uncomplicated"),
    ("Y90.3", "Blood alcohol level of 60-79 mg/100 ml"),
    ("R78.0", "Finding of alcohol in blood"),
]
STIMULANT = [  # cocaine (F14) is "other substance use" in the value sets, not a stimulant
    ("F15.10", "Other stimulant abuse, uncomplicated"),
    ("F15.20", "Other stimulant dependence, uncomplicated"),
]
OTHER_SUD = [
    ("F12.20", "Cannabis dependence, uncomplicated"),
    ("F11.20", "Opioid dependence, uncomplicated"),
    ("F14.10", "Cocaine abuse, uncomplicated"),
    ("F17.210", "Nicotine dependence, cigarettes, uncomplicated"),
]
DEPRESSION = [
    ("F33.1", "Major depressive disorder, recurrent, moderate"),
    ("F32.9", "Major depressive disorder, single episode, unspecified"),
    ("F33.0", "Major depressive disorder, recurrent, mild"),
    ("F34.1", "Dysthymic disorder"),
]
INSOMNIA = [
    ("G47.00", "Insomnia, unspecified"),
    ("F51.01", "Primary insomnia"),
    ("G47.21", "Circadian rhythm sleep disorder, delayed sleep phase type"),
]
ATTENTION = [
    ("R41.840", "Attention and concentration deficit"),
    ("R41.844", "Frontal lobe and executive function deficit"),
]
PTSD = [
    ("F43.10", "Post-traumatic stress disorder, unspecified"),
    ("F43.12", "Post-traumatic stress disorder, chronic"),
]
LEGAL = [
    ("Z65.3", "Problems related to other legal circumstances"),
    ("Z65.1", "Imprisonment and other incarceration"),
]
WORK = [
    ("Z56.0", "Unemployment, unspecified"),
    ("Z55.9", "Problems related to education and literacy, unspecified"),
]
HOUSING = [
    ("Z59.811", "Housing instability, housed, with risk of homelessness"),
    ("Z59.02", "Unsheltered homelessness"),
]
ANTIDEPRESSANTS = [
    ("36437", "sertraline"),
    ("321988", "escitalopram"),
    ("42347", "bupropion"),
    ("39786", "venlafaxine"),
    ("4493", "fluoxetine"),
    ("72625", "duloxetine"),
]
INJURIES = [
    (("S62.302A", "Fracture of metacarpal bone"), ("W01.0XXA", "Fall from slipping, tripping")),
    (("S61.411A", "Laceration of right hand"), ("W26.0XXA", "Contact with knife")),
    (("S93.401A", "Sprain of right ankle"), ("W10.8XXA", "Fall from other stairs and steps")),
]
CRASHES = [
    ("V43.52XA", "Car driver injured in collision with car in traffic accident"),
    ("V47.5XXA", "Car driver injured in collision with fixed object in traffic accident"),
]


def condition(p: PersonaBuilder, code: tuple[str, str], days_ago: int, **kw: Any) -> str:
    return p.condition(code[0], code[1], recorded=ago(days_ago), **kw)


def routine_visits(p: PersonaBuilder, v: int, count: int = 2) -> None:
    for i in range(count):
        when = ago(60 + 200 * i + 7 * v)
        p.encounter("AMB", f"{when}T09:00:00Z", f"{when}T09:30:00Z")


def injury_visit(p: PersonaBuilder, days_ago: int, v: int) -> None:
    when = ago(days_ago)
    visit = p.encounter("EMER", f"{when}T18:00:00Z", f"{when}T22:00:00Z")
    injury, cause = pick(INJURIES, v)
    for code in (injury, cause):
        p.condition(
            code[0], code[1], recorded=when, encounter=visit, category="encounter-diagnosis"
        )


def crash(p: PersonaBuilder, days_ago: int, v: int) -> None:
    when = ago(days_ago)
    visit = p.encounter("EMER", f"{when}T20:00:00Z", f"{when}T23:30:00Z")
    for code in (pick(CRASHES, v), ("S13.4XXA", "Sprain of ligaments of cervical spine")):
        p.condition(
            code[0], code[1], recorded=when, encounter=visit, category="encounter-diagnosis"
        )


def antidepressants(p: PersonaBuilder, v: int, count: int, *, newest_days_ago: int = 60) -> None:
    """``count`` distinct antidepressants, one every 200 days, each dispensed for 90 days."""
    for i in range(count):
        code, name = ANTIDEPRESSANTS[(v + i) % len(ANTIDEPRESSANTS)]
        when = ago(newest_days_ago + 200 * i)
        request = p.medication_request(code, name, when, days=90)
        p.medication_dispense(request, code, name, when, days=90)


# --- archetypes ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Archetype:
    id: str
    title: str
    profile: Profile
    build: Build
    recommendation: str
    signals: frozenset[str] = field(default_factory=frozenset)
    rules_fired: tuple[str, ...] = ()
    safety_gate: str = CLEAR_LIMITED
    style: Style | None = None


def e1(p: PersonaBuilder, v: int) -> None:
    condition(p, pick(STIMULANT, v), 400 + v)
    condition(p, pick(ALCOHOL, v), 700 + v)
    crash(p, 300 + 11 * v, v)
    condition(p, pick(INSOMNIA, v), 500)


def e2(p: PersonaBuilder, v: int) -> None:
    condition(p, pick(ALCOHOL, v + 1), 200 + v)
    condition(p, pick(PTSD, v), 900)
    condition(p, pick(LEGAL, v), 150 + 3 * v)


def e3(p: PersonaBuilder, v: int) -> None:
    injury_visit(p, 100 + 5 * v, v)
    injury_visit(p, 500 + 9 * v, v + 1)
    condition(p, pick(STIMULANT, v + 1), 800)


def e4(p: PersonaBuilder, v: int) -> None:
    crash(p, 600 + 13 * v, v + 1)
    condition(p, pick(OTHER_SUD, v), 250)
    condition(p, pick(WORK, v), 90 + v)
    condition(p, ("F63.81", "Intermittent explosive disorder"), 1000)


def i1(p: PersonaBuilder, v: int) -> None:
    condition(p, pick(DEPRESSION, v), 2000)
    condition(p, ("F41.1", "Generalized anxiety disorder"), 1500)
    condition(p, pick(INSOMNIA, v), 700)
    condition(p, pick(ATTENTION, v), 200)
    antidepressants(p, v, 3)


def i2(p: PersonaBuilder, v: int) -> None:
    condition(p, pick(DEPRESSION, v + 1), 1200)
    condition(p, ("F41.1", "Generalized anxiety disorder"), 900)
    condition(p, ("F60.3", "Borderline personality disorder"), 1000)
    condition(p, pick(INSOMNIA, v + 1), 300)


def i3(p: PersonaBuilder, v: int) -> None:
    condition(p, pick(DEPRESSION, v + 2), 1100)
    condition(p, pick(ALCOHOL, v + 2), 120 + v)
    condition(p, pick(INSOMNIA, v + 2), 400)


def i4(p: PersonaBuilder, v: int) -> None:
    condition(p, ("F41.1", "Generalized anxiety disorder"), 800)
    condition(p, pick(ATTENTION, v + 1), 150)
    condition(p, pick(WORK, v + 1), 260)
    condition(p, ("Z81.8", "Family history of other mental and behavioral disorders"), 1000)


def i5(p: PersonaBuilder, v: int) -> None:
    condition(p, pick(DEPRESSION, v + 3), 1300)
    antidepressants(p, v + 2, 3, newest_days_ago=30)
    condition(p, pick(OTHER_SUD, v + 1), 500)
    condition(p, pick(HOUSING, v), 100)


def l1(p: PersonaBuilder, v: int) -> None:
    when = ago(700 + 3 * v)
    visit = p.encounter("EMER", f"{when}T13:00:00Z", f"{when}T19:00:00Z")
    p.condition(
        "S06.0X1A",
        "Concussion with loss of consciousness of 30 minutes or less",
        recorded=when,
        encounter=visit,
        category="encounter-diagnosis",
    )
    condition(p, ("Z87.820", "Personal history of traumatic brain injury"), 500)
    condition(p, pick(ATTENTION, v), 500)
    condition(p, pick(INSOMNIA, v), 450)


def l2(p: PersonaBuilder, v: int) -> None:
    condition(p, pick(PTSD, v + 1), 1500)
    condition(p, pick(DEPRESSION, v), 1400)
    condition(p, pick(INSOMNIA, v + 1), 1000)


def l3(p: PersonaBuilder, v: int) -> None:
    bipolar = [("F31.9", "Bipolar disorder, unspecified"), ("F31.81", "Bipolar II disorder")]
    condition(p, pick(bipolar, v), 1600)
    condition(p, pick(INSOMNIA, v + 2), 600)


def l4(p: PersonaBuilder, v: int) -> None:
    condition(p, ("F11.20", "Opioid dependence, uncomplicated"), 700 + v)
    condition(p, ("F17.210", "Nicotine dependence, cigarettes, uncomplicated"), 2000)


def l5(p: PersonaBuilder, v: int) -> None:
    condition(p, pick(ALCOHOL, v + 3), 300 + 7 * v)


def c1(p: PersonaBuilder, v: int) -> None:
    condition(p, ("I10", "Essential (primary) hypertension"), 900 + v)
    p.observation("55758-7", "PHQ-2 total score", f"{ago(60 + 7 * v)}T09:05:00Z", value=0)


def c2(p: PersonaBuilder, v: int) -> None:
    p.condition("G47.419", "Narcolepsy without cataplexy", onset="2020", recorded="2020-10-10")
    for days_ago in (160, 130, 100):
        when = ago(days_ago + v)
        request = p.medication_request("725", "amphetamine", when, reason=("G47.419", ""))
        p.medication_dispense(request, "725", "amphetamine", when)


def s1(p: PersonaBuilder, v: int) -> None:
    """Sparse: the one routine visit that every patient gets, and nothing else."""


def b1(p: PersonaBuilder, v: int) -> None:
    condition(p, pick(ALCOHOL, v), 400)
    condition(p, pick(PTSD, v), 1000)


def b2(p: PersonaBuilder, v: int) -> None:
    crash(p, 1096, v)
    condition(p, pick(ALCOHOL, v + 1), 200)
    condition(p, pick(LEGAL, v), 250)


def b3(p: PersonaBuilder, v: int) -> None:
    crash(p, 1095, v)
    condition(p, pick(ALCOHOL, v + 1), 200)


def g1(p: PersonaBuilder, v: int) -> None:
    condition(p, ("R45.851", "Suicidal ideations"), 30 + v)
    condition(p, pick(STIMULANT, v), 400)
    condition(p, pick(ALCOHOL, v), 500)


def x1(p: PersonaBuilder, v: int) -> None:
    condition(p, ("F90.0", "ADHD, predominantly inattentive type"), 900)
    condition(p, pick(ALCOHOL, v), 300)
    crash(p, 200 + v, v)


def _s(*names: str) -> frozenset[str]:
    return frozenset(names)


BOTH = ("high_with_modifiers", "two_high_classes")
HWM = ("high_with_modifiers",)
TWO = ("two_high_classes",)

ARCHETYPES: tuple[Archetype, ...] = (
    Archetype("E1", "Stimulant and alcohol disorders, a crash as driver, insomnia",
              "suggestive", e1, CONSIDER,
              _s("stimulant_related_disorder", "alcohol_involvement", "crash_as_driver",
                 "insomnia"), TWO, style="externalizing"),
    Archetype("E2", "Alcohol involvement with PTSD and legal problems",
              "suggestive", e2, CONSIDER,
              _s("alcohol_involvement", "ptsd", "legal_problems"), HWM, style="externalizing"),
    Archetype("E3", "Two accidental injury visits and a stimulant disorder",
              "suggestive", e3, CONSIDER,
              _s("repeated_accidental_injury", "stimulant_related_disorder"), TWO,
              style="externalizing"),
    Archetype("E4", "A crash as driver, other substance use, unemployment, intermittent "
              "explosive disorder",
              "suggestive", e4, CONSIDER,
              _s("crash_as_driver", "other_substance_use", "education_occupation_problems",
                 "intermittent_explosive_disorder"),
              HWM, style="externalizing"),
    Archetype("I1", "Recurrent depression, anxiety, insomnia, attention symptoms, "
              "three antidepressants", "suggestive", i1, NO_REC,
              _s("depression_or_anxiety", "insomnia", "attention_symptoms",
                 "multiple_antidepressants"), style="internalizing"),
    Archetype("I2", "Depression, anxiety, borderline personality, insomnia",
              "suggestive", i2, NO_REC,
              _s("depression_or_anxiety", "borderline_personality", "insomnia"),
              style="internalizing"),
    Archetype("I3", "Depression and insomnia with alcohol involvement",
              "suggestive", i3, CONSIDER,
              _s("depression_or_anxiety", "alcohol_involvement", "insomnia"), HWM,
              style="internalizing"),
    Archetype("I4", "Anxiety, attention symptoms, work or study problems, family history",
              "suggestive", i4, NO_REC,
              _s("depression_or_anxiety", "attention_symptoms",
                 "education_occupation_problems", "family_history"),
              style="internalizing"),
    Archetype("I5", "Depression, three antidepressants, other substance use, housing "
              "problems", "suggestive", i5, NO_REC,
              _s("depression_or_anxiety", "multiple_antidepressants", "other_substance_use",
                 "housing_problems"), style="internalizing"),
    Archetype("L1", "TBI look-alike: concussion, attention symptoms, insomnia",
              "not_suggestive", l1, NO_REC, _s("tbi_overlap", "attention_symptoms", "insomnia")),
    Archetype("L2", "PTSD look-alike: PTSD, depression, insomnia",
              "not_suggestive", l2, NO_REC, _s("ptsd", "depression_or_anxiety", "insomnia")),
    Archetype("L3", "Bipolar look-alike: bipolar disorder and insomnia",
              "not_suggestive", l3, NO_REC, _s("insomnia")),
    Archetype("L4", "Substance use without ADHD signals: opioid and nicotine dependence",
              "not_suggestive", l4, NO_REC, _s("other_substance_use")),
    Archetype("L5", "Alcohol involvement alone", "not_suggestive", l5, NO_REC,
              _s("alcohol_involvement")),
    Archetype("C1", "Healthy control: routine visits, hypertension, a negative screen",
              "not_suggestive", c1, NO_REC),
    Archetype("C2", "Narcolepsy treated with a stimulant", "not_suggestive", c2, NO_REC),
    Archetype("S1", "Sparse record: one routine visit", "not_suggestive", s1, NO_REC),
    Archetype("S2", "Empty record", "not_applicable", s1, "insufficient_data"),
    Archetype("B1", "Narrow miss: alcohol involvement and PTSD only", "boundary", b1, NO_REC,
              _s("alcohol_involvement", "ptsd")),
    Archetype("B2", "Window miss: the crash is one day outside 1095 days", "boundary", b2,
              NO_REC, _s("alcohol_involvement", "legal_problems")),
    Archetype("B3", "Window edge: the crash is exactly 1095 days ago", "boundary", b3,
              CONSIDER, _s("alcohol_involvement", "crash_as_driver"), TWO),
    Archetype("G1", "Safety gate: recent suicidal ideation code, stimulant and alcohol "
              "disorders", "not_applicable", g1, "address_safety_gate_first",
              _s("stimulant_related_disorder", "alcohol_involvement"), TWO,
              safety_gate="positive"),
    Archetype("X1", "Already in care: an ADHD code, alcohol involvement, a crash",
              "not_applicable", x1, "already_in_care",
              _s("alcohol_involvement", "crash_as_driver"), TWO),
)  # fmt: skip


@dataclass(frozen=True)
class CohortPatient:
    patient_id: str
    archetype: Archetype
    sex: str
    age_band: str
    variant: int
    resources: list[Resource]


def build_patient(
    archetype: Archetype, sex: str, age_band: str, index: int, variant: int
) -> CohortPatient:
    # Age on the as-of date is the band's age or one less: inside the band either way.
    birth = date(AS_OF.year - AGE_BANDS[age_band], 1 + variant % 12, 1 + (index * 7) % 28)
    p = PersonaBuilder(
        f"c{index:03d}", gender=sex, birth_date=birth.isoformat(), number=20000 + index
    )
    if archetype.id != "S2":  # the empty record has nothing but the patient
        routine_visits(p, variant, count=1 if archetype.id == "S1" else 2)
    archetype.build(p, variant)
    return CohortPatient(p.patient_id, archetype, sex, age_band, variant, p.resources)


def build_cohort(archetypes: tuple[Archetype, ...] = ARCHETYPES) -> list[CohortPatient]:
    """Every archetype for every sex and age band, deterministic."""
    patients = []
    index = 0
    for archetype in archetypes:
        for variant, (sex, band) in enumerate((s, b) for s in SEXES for b in AGE_BANDS):
            index += 1
            patients.append(build_patient(archetype, sex, band, index, variant))
    return patients


def all_resources(patients: list[CohortPatient]) -> list[Resource]:
    return [r for p in patients for r in p.resources]
