from pytest_bdd import given, parsers, then, when


@given("用户在 TodoMVC 首页")
def app_started(android_driver):
    """Android application is started."""
    pass


@when(parsers.parse('用户创建任务 "{task_name}"'))
def create_task(android_driver, task_name: str):
    """Create a task in Android app."""
    pass


@then(parsers.parse('页面显示任务 "{task_name}"'))
def task_created_successfully(android_driver, task_name: str):
    """Verify task was created successfully."""
    pass
