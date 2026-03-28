# Shared steps that can be used across different platforms
from pytest_bdd import given, then, when


@given("用户在应用首页")
def user_on_app_home():
    """Common step for user being on app home page."""
    pass
