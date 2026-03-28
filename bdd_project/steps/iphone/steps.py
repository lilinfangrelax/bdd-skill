from pytest_bdd import given, parsers, then, when


@given("用户在 TodoMVC 首页")
def app_started(ios_driver):
    pass


@when(parsers.parse('用户创建任务 "{task_name}"'))
def create_task(ios_driver, task_name: str):
    pass


@then(parsers.parse('页面显示任务 "{task_name}"'))
def task_created_successfully(ios_driver, task_name: str):
    pass
