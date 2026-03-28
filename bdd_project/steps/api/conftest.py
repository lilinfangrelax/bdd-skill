import pytest
import requests


@pytest.fixture
def api_client():
    """HTTP 请求用的 API 客户端 fixture。"""
    session = requests.Session()
    yield session
    session.close()


@pytest.fixture
def api_base_url():
    """API 测试的基础 URL。"""
    return "http://localhost:8080/api"
