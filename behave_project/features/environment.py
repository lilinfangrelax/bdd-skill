"""behave 测试框架的环境配置模块。

提供 Playwright 浏览器实例的生命周期管理：
- before_all: 启动浏览器，创建页面上下文
- after_all: 关闭浏览器，清理资源
"""

from __future__ import annotations

import os

from playwright.sync_api import sync_playwright


def before_all(context):
    """测试开始前初始化 Playwright 浏览器环境。

    创建浏览器实例、上下文和页面，并存入 context 供后续步骤使用。
    """
    base_url = os.environ.get("DEMO_BASE_URL", "http://127.0.0.1:8765/")
    context.base_url = base_url.rstrip("/") + "/"
    context._pw = sync_playwright().start()
    context.browser = context._pw.chromium.launch(headless=True)
    context.browser_context = context.browser.new_context()
    context.page = context.browser_context.new_page()


def after_all(context):
    """测试结束后关闭 Playwright 浏览器环境。

    按依赖关系逆序关闭：page -> browser_context -> browser -> playwright。
    """
    if hasattr(context, "page"):
        context.page.close()
    if hasattr(context, "browser_context"):
        context.browser_context.close()
    if hasattr(context, "browser"):
        context.browser.close()
    if hasattr(context, "_pw"):
        context._pw.stop()
