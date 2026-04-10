"""终端界面（TUI）步骤定义（占位，待接入自动化）。"""

from pytest_bdd import given, parsers, then, when


@given("用户在 TodoMVC 首页")
def app_started(terminal_session):
    pass


@when(parsers.parse('用户创建任务 "{task_name}"'))
def create_task(terminal_session, task_name: str):
    pass


@then(parsers.parse('页面显示任务 "{task_name}"'))
def task_created_successfully(terminal_session, task_name: str):
    pass
