from pytest_bdd import given, when, then, parsers

@given("I open the browser")
def open_browser(page):
    pass

@when(parsers.parse('I navigate to "{url}"'))
def navigate_to(page, url):
    page.goto(url)

@then(parsers.parse('I should see the page title "{title}"'))
def check_page_title(page, title):
    assert page.title() == title
