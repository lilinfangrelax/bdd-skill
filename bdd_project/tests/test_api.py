"""使用 pytest-bdd 的 API 测试。"""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.api.conftest",
    "bdd_project.steps.api.steps",
]


@pytest.mark.api
@scenario("../features/task.feature", "用户创建任务")
def test_api_scenario():
    """执行 API 场景。"""
    pass
