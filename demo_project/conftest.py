import logging
import os
import sys
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from support.api_service import ApiService
from support.http_client import HttpClient
from support.template_engine import TemplateEngine

# 将 demo_project 根目录加入导入路径，确保 steps/support 可被 pytest 发现。
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@pytest.fixture(scope="session")
def playwright():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright):
    browser = playwright.chromium.launch(headless=False)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def page(browser):
    page = browser.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """读取 API 基础地址，默认指向 GitHub 公共 API。"""
    return os.environ.get("API_BASE_URL", "https://api.github.com")


@pytest.fixture(scope="session")
def templates_dir() -> str:
    """模板目录。"""
    return str(Path(__file__).parent / "templates")


@pytest.fixture(scope="session")
def http_client(api_base_url):
    """初始化并复用 HTTP 客户端。"""
    client = HttpClient(
        base_url=api_base_url,
        default_headers={"X-App-Version": "1.0"},
        timeout=30,
    )
    yield client
    client.session.close()


@pytest.fixture(scope="session")
def template_engine(templates_dir):
    """初始化模板引擎。"""
    return TemplateEngine(templates_dir=templates_dir)


@pytest.fixture(scope="session")
def api_service(http_client, template_engine):
    """初始化 API 业务编排服务。"""
    return ApiService(http_client=http_client, template_engine=template_engine)


@pytest.fixture(scope="session")
def global_vars():
    """跨场景共享变量。"""
    return {}


@pytest.fixture(scope="function")
def scenario_state(global_vars):
    """场景级运行时变量，映射 Behave 的 before_scenario 生命周期。"""
    return {
        "vars": dict(global_vars),
        "response": None,
        "response_json": None,
    }