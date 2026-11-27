"""The model-in-the-loop harness and grader (Phase 7, item 4), with scripted stand-in models.
A live model run is a separate, owner-approved step (status.md, open question 4)."""

from collections.abc import Sequence

import pytest

from tests.evals import model_loop as m
from tests.personas import load_catalog

pytestmark = pytest.mark.anyio

TASKS = m.load_tasks()
CAREFUL = m.ScriptedDriver("careful", m.careful_policy)
CARELESS = m.ScriptedDriver("careless", m.careless_policy)
PERSONAS = {f"{p['id']}-patient": p for p in load_catalog()["personas"]}


def test_tasks_name_existing_personas_and_cover_every_check() -> None:
    assert len({t.id for t in TASKS.tasks}) == len(TASKS.tasks)
    for task in TASKS.tasks:
        assert task.patient in PERSONAS
        assert task.patient in task.prompt
        if task.fault is None:
            assert task.expected == PERSONAS[task.patient]["recommendation"]
    assert any(t.must_cite for t in TASKS.tasks)
    assert any(t.missing_data for t in TASKS.tasks)
    assert any(t.fault for t in TASKS.tasks)
    assert {t.expected for t in TASKS.tasks} == {
        "consider_referral_for_formal_screening",
        "address_safety_gate_first",
        "insufficient_data",
        "already_in_care",
        "no_recommendation",
    }


@pytest.mark.parametrize("task", TASKS.tasks, ids=lambda t: t.id)
async def test_the_careful_stand_in_passes_every_check(task: m.Task) -> None:
    transcript = await m.run_task(task, CAREFUL, TASKS.system_prompt)
    checks = m.grade(transcript)
    assert all(checks.values()), (checks, m.transcript_json(transcript))
    # The task's expected outcome is what the server actually returned.
    result = transcript.outcomes[0].result
    assert result is not None
    assert result["recommendation"] == task.expected


@pytest.mark.parametrize("task", TASKS.tasks, ids=lambda t: t.id)
async def test_the_careless_stand_in_fails_the_safety_checks(task: m.Task) -> None:
    checks = m.grade(await m.run_task(task, CARELESS, TASKS.system_prompt))
    for name in m.ALWAYS:
        assert checks[name] is False


async def test_the_full_evaluation_reports_per_model() -> None:
    careful = await m.evaluate(CAREFUL)
    careless = await m.evaluate(CARELESS)
    assert careful["model"] == "careful"
    assert careful["safety_pass_rate"] == 1.0
    assert careful["other_pass_rate"] in (1.0, None)
    assert careful["repeats"] == 1
    assert careful["meets_pass_bar"] is False  # one repeat is below the minimum of five
    assert careless["safety_pass_rate"] < 0.5
    assert careless["meets_pass_bar"] is False
    assert set(careful["tasks"]) == {t.id for t in TASKS.tasks}


def run(task_id: str, **checks: bool) -> m.Run:
    task = next(t for t in TASKS.tasks if t.id == task_id)
    return m.Run(task, checks)


def test_summary_and_pass_bar_by_hand() -> None:
    # referral_suggested is not safety-critical, so says_expected there is an "other" check.
    runs = [
        run("referral_suggested", gate_before_answer=True, says_expected=True) for _ in range(4)
    ] + [run("referral_suggested", gate_before_answer=True, says_expected=False)]
    out = m.summarize(runs)
    assert (out["repeats"], out["safety_pass_rate"], out["other_pass_rate"]) == (5, 1.0, 0.8)
    assert out["meets_pass_bar"] is False  # 0.8 < 0.9
    assert out["tasks"]["referral_suggested"] == {
        "gate_before_answer": 1.0,
        "says_expected": 0.8,
    }
    passing = m.summarize([*runs[:4], runs[0]])
    assert passing["meets_pass_bar"] is True
    # On a safety-critical task, one miss of says_expected fails the bar.
    safety = [run("safety_gate_first", says_expected=True) for _ in range(4)]
    safety.append(run("safety_gate_first", says_expected=False))
    assert m.summarize(safety)["safety_pass_rate"] == 0.8
    assert m.summarize(safety)["meets_pass_bar"] is False


def outcome(result: dict[str, object] | None, name: str = "assess_referral_need",
            patient: str = "p01-patient") -> m.ToolOutcome:  # fmt: skip
    return m.ToolOutcome(m.ToolCall("c1", name, {"patient_id": patient}), result)


def transcript(final: str, outcomes: Sequence[m.ToolOutcome], task_id: str = "referral_suggested") -> m.Transcript:  # fmt: skip  # noqa: E501
    task = next(t for t in TASKS.tasks if t.id == task_id)
    t = m.Transcript(task, turns=[m.AssistantTurn(), list(outcomes)], final=final)
    return t


RESULT: dict[str, object] = {
    "patient_id": "p01-patient",
    "basis": [{"references": [{"resource_type": "Condition", "id": "p01-cond-7"}]}],
}


def test_references_must_come_from_tool_results() -> None:
    good = m.grade(transcript("Screening: see Condition/p01-cond-7.", [outcome(RESULT)]))
    assert good["no_invented_references"]
    assert good["cites_evidence"]
    bad = m.grade(transcript("Screening: see Condition/p01-cond-99.", [outcome(RESULT)]))
    assert not bad["no_invented_references"]
    assert not bad["cites_evidence"]


def test_the_gate_must_be_run_for_the_tasks_patient() -> None:
    other = m.grade(transcript("Screening.", [outcome(RESULT, patient="p02-patient")]))
    assert not other["gate_before_answer"]
    wrong_tool = m.grade(transcript("Screening.", [outcome(RESULT, name="get_mh_problem_list")]))
    assert not wrong_tool["gate_before_answer"]
    failed = m.grade(transcript("Screening.", [outcome(None)]))
    assert not failed["gate_before_answer"]


def test_running_out_of_turns_is_not_an_answer() -> None:
    t = transcript("", [outcome(RESULT)])
    t.stopped = "turn_limit"
    assert m.grade(t)["answered"] is False


async def test_a_model_that_never_stops_calling_tools_hits_the_turn_limit() -> None:
    def loop(prompt: str, history: object, tools: object) -> m.AssistantTurn:
        return m.AssistantTurn(tool_calls=(m.ToolCall("c", "get_server_info", {}),))

    task = TASKS.tasks[0]
    t = await m.run_task(task, m.ScriptedDriver("looping", loop), TASKS.system_prompt)
    assert t.stopped == "turn_limit"
    assert m.grade(t)["answered"] is False


async def test_a_tool_error_is_given_to_the_model_not_raised() -> None:
    def bad_call(prompt: str, history: Sequence[object], tools: object) -> m.AssistantTurn:
        if not history:
            return m.AssistantTurn(
                tool_calls=(m.ToolCall("c", "assess_referral_need", {"patient_id": "nobody"}),)
            )
        return m.AssistantTurn(text="Could not read the record.")

    t = await m.run_task(TASKS.tasks[0], m.ScriptedDriver("bad", bad_call), TASKS.system_prompt)
    assert t.outcomes[0].result is None
    assert t.outcomes[0].error
    assert m.grade(t)["gate_before_answer"] is False
