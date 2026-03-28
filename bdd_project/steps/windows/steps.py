from pytest_bdd import given, parsers, then, when


@given("Windows 应用已启动")
def windows_app_started(windows_app):
    """Windows application is started."""
    pass


@when(parsers.parse('点击 "{button_name}" 按钮'))
def click_button(windows_app, button_name: str):
    """Click a button in Windows app."""
    pass


@then(parsers.parse('窗口标题包含 "{title}"'))
def check_window_title(windows_app, title: str):
    """Verify window title contains expected text."""
    pass
