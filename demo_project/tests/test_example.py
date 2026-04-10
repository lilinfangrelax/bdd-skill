"""使用 pytest-bdd 的测试。"""

import pytest
from pytest_bdd import scenario


pytest_plugins = [
    "steps.example_steps",
]


@scenario("../features/example.feature", "导航到GitHub")
def test_navigate_to_github():
    """执行场景。"""
    pass
