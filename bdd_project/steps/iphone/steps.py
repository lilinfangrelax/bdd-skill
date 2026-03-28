from pytest_bdd import given, parsers, then, when


@given("iOS 应用已启动")
def ios_app_started(ios_driver):
    """iOS application is started."""
    pass


@when(parsers.parse('滑动到 "{direction}"'))
def swipe(ios_driver, direction: str):
    """Swipe in a direction on iOS app."""
    pass


@then(parsers.parse('元素 "{element_id}" 可见'))
def check_element_visible(ios_driver, element_id: str):
    """Verify element is visible on screen."""
    pass
