import pytest


@pytest.fixture
def android_driver():
    """Android driver fixture for mobile testing."""
    # Add Appium/Android driver setup
    driver = None
    yield driver
    if driver:
        driver.quit()
