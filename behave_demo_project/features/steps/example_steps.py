from behave import given, when, then


@given("我打开浏览器")
def open_browser(context):
    # Browser/page are created in environment hooks.
    assert context.page is not None


@when('我导航到 "{url}"')
def navigate_to(context, url):
    context.page.goto(url)


@then('我应该看到页面标题 "{title}"')
def check_page_title(context, title):
    assert context.page.title() == title
