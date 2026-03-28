from pytest_bdd import given, parsers, then, when


@given("应用已启动")
def app_started(terminal_session):
    """TUI application is started."""
    pass


@when(parsers.parse('用户创建任务 "{task_name}"'))
def create_task(terminal_session, task_name: str):
    """Create a task in TUI app."""
    pass


@then("任务创建成功")
def task_created_successfully(terminal_session):
    """Verify task was created successfully."""
    pass
