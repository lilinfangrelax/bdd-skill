import time
from pathlib import Path

from playwright.sync_api import Playwright, sync_playwright

# 与 recordings 同级的 traces/（已在 .gitignore，体积大勿提交）
_TRACES_DIR = Path(__file__).resolve().parent.parent / "traces"


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="chrome", headless=False)
    context = browser.new_context()
    _TRACES_DIR.mkdir(parents=True, exist_ok=True)
    trace_zip = _TRACES_DIR / "task_trace.zip"
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    page.goto("http://127.0.0.1:8765/")

    # 新增任务
    page.get_by_role("textbox", name="任务名称").click()
    page.get_by_role("textbox", name="任务名称").fill("新增任务xxx")
    page.get_by_role("textbox", name="开始日期").click()
    page.get_by_role("textbox", name="开始日期").fill("2025-01-01")
    page.get_by_role("textbox", name="完成日期").click()
    page.get_by_role("textbox", name="完成日期").fill("2026-03-03")
    page.get_by_label("优先级 高 中 低").select_option("高")
    page.get_by_role("textbox", name="描述").click()
    page.get_by_role("textbox", name="描述").fill("任务描述")
    page.get_by_role("button", name="新增任务（POST /api/tasks/create）").click()

    # 编辑任务
    page.get_by_role("button", name="编辑").click()
    page.get_by_role("textbox", name="任务名称").fill("新增任务xxx-修改任务")
    page.get_by_role("button", name="保存修改（POST /api/tasks/update）").click()

    # 假删除任务
    page.get_by_role("button", name="假删除").click()

    # 永久删除任务
    page.get_by_role("cell", name="永久删除").click()

    # ---------------------
    time.sleep(3)
    context.tracing.stop(path=str(trace_zip))
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
