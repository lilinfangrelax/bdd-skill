"""API 层步骤定义（占位，待接入真实接口）。"""

from pytest_bdd import given, parsers, then, when


@given("用户在 TodoMVC 首页")
def app_started(http_client):
    pass


@when(parsers.parse('用户创建任务 "{task_name}"'))
def create_task(http_client, task_name: str):
    pass


@then(parsers.parse('页面显示任务 "{task_name}"'))
def task_created_successfully(http_client, task_name: str):
    pass
