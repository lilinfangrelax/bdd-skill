"""使用 pytest-bdd 与 Playwright 的 Web UI 测试。"""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.web.conftest",
    "bdd_project.steps.web.steps",
]


@pytest.mark.web
@scenario("../features/task.feature", "用户创建任务")
def test_web_scenario():
    """执行 Web UI 场景。"""
    pass
