"""
TUI (Terminal User Interface) tests using pytest-bdd.
"""

import pytest
from pytest_bdd import scenario

pytest_plugins = ["bdd_project.steps.tui.steps"]


@pytest.mark.tui
@scenario("../features/task.feature", "用户创建任务")
def test_tui_scenario():
    """Run TUI scenario."""
    pass
