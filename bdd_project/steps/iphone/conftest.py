import pytest


@pytest.fixture
def ios_driver():
    """iOS driver fixture for mobile testing."""
    # Add Appium/iOS driver setup
    driver = None
    yield driver
    if driver:
        driver.quit()
