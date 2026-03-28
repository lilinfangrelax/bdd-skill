"""macos tests using pytest-bdd."""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.macos.conftest",
    "bdd_project.steps.macos.steps",
]


@pytest.mark.macos
@scenario("../features/task.feature", "用户创建任务")
def test_macos_scenario():
    pass
