"""Web UI tests using pytest-bdd and Playwright."""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.web.conftest",
    "bdd_project.steps.web.steps",
]


@pytest.mark.web
@scenario("../features/task.feature", "用户创建任务")
def test_web_scenario():
    """Run Web UI scenario."""
    pass
