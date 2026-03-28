"""
API tests using pytest-bdd.
"""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.api.conftest",
    "bdd_project.steps.api.steps",
]


@pytest.mark.api
@scenario("../features/task.feature", "用户创建任务")
def test_api_scenario():
    """Run API scenario."""
    pass
