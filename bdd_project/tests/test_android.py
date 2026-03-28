"""使用 pytest-bdd 的 Android 移动端测试。"""

import pytest
from pytest_bdd import scenario

pytest_plugins = [
    "bdd_project.steps.android.conftest",
    "bdd_project.steps.android.steps",
]


@pytest.mark.android
@scenario("../features/task.feature", "用户创建任务")
def test_android_scenario():
    """执行 Android 移动端场景。"""
    pass
