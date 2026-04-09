"""behave 测试步骤定义模块。

定义 Gherkin 步骤对应的 Python 实现，使用 Playwright 进行页面操作。
"""

from __future__ import annotations

from behave import given, then


@given("打开任务演示页面")
def step_open_demo_page(context):
    """打开任务演示页面的 Given 步骤实现。

    导航至 base_url 指定的演示页面。
    """
    context.page.goto(context.base_url)


@then('页面标题包含 "{keyword}"')
def step_check_page_title(context, keyword):
    """验证页面标题包含指定关键字的 Then 步骤实现。

    Args:
        keyword: 期望标题中包含的关键字。

    Raises:
        AssertionError: 若标题不包含关键字则抛出断言错误。
    """
    title = context.page.title()
    assert keyword in title, f"页面标题不包含关键字: {keyword}, 实际标题: {title}"
