from pytest_bdd import given, parsers, then, when


@given("应用已启动")
def app_started(ios_driver):
    """iOS application is started."""
    pass


@when(parsers.parse('用户创建任务 "{task_name}"'))
def create_task(ios_driver, task_name: str):
    """Create a task in iOS app."""
    pass


@then("任务创建成功")
def task_created_successfully(ios_driver):
    """Verify task was created successfully."""
    pass
