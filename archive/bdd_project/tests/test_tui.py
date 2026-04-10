"""使用 pytest-bdd 的终端界面（TUI）测试。"""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.tui.conftest",
    "bdd_project.steps.tui.steps",
]


@pytest.mark.tui
@scenario("../features/task.feature", "用户创建任务")
def test_tui_scenario():
    """执行 TUI 场景。"""
    pass
