"""
iOS/iPhone mobile tests using pytest-bdd.
"""

import pytest
from pytest_bdd import scenario

pytest_plugins = ["bdd_project.steps.iphone.steps"]


@pytest.mark.iphone
@scenario("../features/task.feature", "用户创建任务")
def test_iphone_scenario():
    """Run iOS mobile scenario."""
    pass
