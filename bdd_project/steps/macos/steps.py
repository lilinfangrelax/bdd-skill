from pytest_bdd import given, parsers, then, when


@given("macOS 应用已启动")
def macos_app_started(macos_app):
    """macOS application is started."""
    pass


@when(parsers.parse('点击菜单 "{menu_name}"'))
def click_menu(macos_app, menu_name: str):
    """Click a menu item in macOS app."""
    pass


@then(parsers.parse('对话框显示 "{message}"'))
def check_dialog(macos_app, message: str):
    """Verify dialog shows expected message."""
    pass
