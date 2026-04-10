"""使用 pytest-bdd 的 macOS 桌面测试。"""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.macos.conftest",
    "bdd_project.steps.macos.steps",
]


@pytest.mark.macos
@scenario("../features/task.feature", "用户创建任务")
def test_macos_scenario():
    """执行 macOS 桌面场景。"""
    pass
