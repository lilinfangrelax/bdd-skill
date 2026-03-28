from pytest_bdd import given, parsers, then, when


@given("终端应用已启动")
def tui_app_started(terminal_session):
    """TUI application is started."""
    pass


@when(parsers.parse('输入命令 "{command}"'))
def type_command(terminal_session, command: str):
    """Type a command in terminal."""
    pass


@then(parsers.parse('输出包含 "{text}"'))
def check_output_contains(terminal_session, text: str):
    """Verify terminal output contains expected text."""
    pass
