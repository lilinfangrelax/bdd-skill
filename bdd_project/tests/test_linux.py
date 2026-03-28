"""使用 pytest-bdd 的 Linux 桌面测试。"""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.linux.conftest",
    "bdd_project.steps.linux.steps",
]


@pytest.mark.linux
@scenario("../features/task.feature", "用户创建任务")
def test_linux_scenario():
    """执行 Linux 桌面场景。"""
    pass
