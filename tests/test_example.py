"""使用 pytest-bdd 的测试。"""

import pytest
from pytest_bdd import scenario


pytest_plugins = [
    "steps.example_steps",
]


@scenario("../features/example.feature", "Navigate to example.com")
def test_navigate_to_examplecom():
    """执行场景。"""
    pass
