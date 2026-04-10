"""使用 pytest-bdd 的 iPhone / iOS 测试。"""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.iphone.conftest",
    "bdd_project.steps.iphone.steps",
]


@pytest.mark.iphone
@scenario("../features/task.feature", "用户创建任务")
def test_iphone_scenario():
    """执行 iOS 场景。"""
    pass
