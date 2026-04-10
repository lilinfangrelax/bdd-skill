import pytest


@pytest.fixture
def ios_driver():
    """移动端 iOS 测试用的驱动 fixture。"""
    # 后续可在此接入 Appium / iOS 驱动
    driver = None
    yield driver
    if driver:
        driver.quit()
