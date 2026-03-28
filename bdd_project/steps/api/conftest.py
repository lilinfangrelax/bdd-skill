import pytest
import requests


@pytest.fixture
def api_client():
    """API client fixture for HTTP requests."""
    session = requests.Session()
    yield session
    session.close()


@pytest.fixture
def api_base_url():
    """Base URL for API tests."""
    return "http://localhost:8080/api"
