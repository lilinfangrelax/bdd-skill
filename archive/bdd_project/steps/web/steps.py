"""Web 端步骤定义（依赖 bdd_project.steps.web.conftest 中的 page fixture）。"""

from playwright.sync_api import Page
from pytest_bdd import given, parsers, then, when


@given("用户在 TodoMVC 首页")
def user_on_home(page: Page):
    """打开 TodoMVC 示例首页。"""
    page.goto("https://todomvc.com/examples/vue/dist/#/")


@when(parsers.parse('用户创建任务 "{task_name}"'))
def create_task(page: Page, task_name: str):
    """在输入框中创建任务并回车确认。"""
    input_box = page.locator(".new-todo")
    input_box.fill(task_name)
    input_box.press("Enter")


@then(parsers.parse('页面显示任务 "{task_name}"'))
def check_task(page: Page, task_name: str):
    """断言列表中显示指定任务标题。"""
    task = page.locator(".todo-list li .view label")
    assert task.inner_text() == task_name
