from pytest_bdd import given, parsers, then, when


@given("应用已启动")
def app_started(linux_app):
    """Linux application is started."""
    pass


@when(parsers.parse('用户创建任务 "{task_name}"'))
def create_task(linux_app, task_name: str):
    """Create a task in Linux app."""
    pass


@then("任务创建成功")
def task_created_successfully(linux_app):
    """Verify task was created successfully."""
    pass
