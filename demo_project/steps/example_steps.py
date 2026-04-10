from pytest_bdd import given, when, then, parsers

@given("我打开浏览器")
def open_browser(page):
    pass

@when(parsers.parse('我导航到 "{url}"'))
def navigate_to(page, url):
    page.goto(url)

@then(parsers.parse('我应该看到页面标题 "{title}"'))
def check_page_title(page, title):
    assert page.title() == title
