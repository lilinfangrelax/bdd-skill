"""Android 移动端步骤定义（占位，待接入自动化）。"""

from pytest_bdd import given, parsers, then, when


@given("用户在 TodoMVC 首页")
def app_started(android_driver):
    """Android 应用已启动。"""
    pass


@when(parsers.parse('用户创建任务 "{task_name}"'))
def create_task(android_driver, task_name: str):
    """在 Android 应用中创建任务。"""
    pass


@then(parsers.parse('页面显示任务 "{task_name}"'))
def task_created_successfully(android_driver, task_name: str):
    """校验任务创建成功。"""
    pass
