"""
Linux desktop tests using pytest-bdd.
"""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.linux.conftest",
    "bdd_project.steps.linux.steps",
]


@pytest.mark.linux
@scenario("../features/task.feature", "用户创建任务")
def test_linux_scenario():
    """Run Linux desktop scenario."""
    pass
