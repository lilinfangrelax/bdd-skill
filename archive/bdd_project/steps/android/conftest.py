import pytest


@pytest.fixture
def android_driver():
    """移动端 Android 测试用的驱动 fixture。"""
    # 后续可在此接入 Appium / Android 驱动
    driver = None
    yield driver
    if driver:
        driver.quit()
