from pytest_bdd import given, parsers, then, when


@given("Linux 应用已启动")
def linux_app_started(linux_app):
    """Linux application is started."""
    pass


@when(parsers.parse('执行快捷键 "{shortcut}"'))
def press_shortcut(linux_app, shortcut: str):
    """Press keyboard shortcut in Linux app."""
    pass


@then(parsers.parse('应用状态为 "{state}"'))
def check_app_state(linux_app, state: str):
    """Verify application state."""
    pass
