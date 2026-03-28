from pytest_bdd import given, parsers, then, when


@given("Android 应用已启动")
def android_app_started(android_driver):
    """Android application is started."""
    pass


@when(parsers.parse('点击元素 "{element_id}"'))
def tap_element(android_driver, element_id: str):
    """Tap on an element in Android app."""
    pass


@then(parsers.parse('显示文本 "{text}"'))
def check_text_displayed(android_driver, text: str):
    """Verify text is displayed on screen."""
    pass
