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
    """API 测试的基础 URL（仅 origin；与 fixture 中 path 如 /api/tasks/... 拼接）。"""
    return "http://localhost:8765"
