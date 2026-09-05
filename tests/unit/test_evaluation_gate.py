import pytest

from scripts.run_evaluation import release_gate_passes


def passing_case():
    return dict.fromkeys((
        "hard_constraints", "replan", "loop_terminated", "task_completed_end_to_end",
    ), True)


def test_evaluation_requires_nonempty_passing_cases():
    assert not release_gate_passes([])
    assert release_gate_passes([passing_case(), passing_case()])


@pytest.mark.parametrize("key", list(passing_case()))
def test_evaluation_rejects_failure_or_missing_check(key):
    case = passing_case()
    case[key] = False
    assert not release_gate_passes([case])
    del case[key]
    assert not release_gate_passes([case])
