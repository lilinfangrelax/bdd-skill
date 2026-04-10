import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture
def page():
    """Web 测试使用的 Playwright 页面对象（单独跑 web 用例时不依赖 pytest-playwright 插件）。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page_obj = browser.new_page()
        yield page_obj
        browser.close()
