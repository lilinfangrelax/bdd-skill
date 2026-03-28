"""windows tests using pytest-bdd."""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.windows.conftest",
    "bdd_project.steps.windows.steps",
]


@pytest.mark.windows
@scenario("../features/task.feature", "用户创建任务")
def test_windows_scenario():
    pass
