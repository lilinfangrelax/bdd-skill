from playwright.sync_api import sync_playwright


def before_all(context):
    context._playwright_manager = sync_playwright()
    context.playwright = context._playwright_manager.start()
    context.browser = context.playwright.chromium.launch(headless=False)


def before_scenario(context, scenario):
    context.page = context.browser.new_page()


def after_scenario(context, scenario):
    if hasattr(context, "page") and context.page:
        context.page.close()


def after_all(context):
    if hasattr(context, "browser") and context.browser:
        context.browser.close()
    if hasattr(context, "_playwright_manager") and context._playwright_manager:
        context._playwright_manager.stop()
