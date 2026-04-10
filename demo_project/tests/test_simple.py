from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import sync_playwright

# Define scenarios
scenarios('../features/example.feature')

# Define fixtures
@given("I open the browser")
def open_browser():
    pass

@when(parsers.parse('I navigate to "{url}"'))
def navigate_to(page, url):
    page.goto(url)

@then(parsers.parse('I should see the page title "{title}"'))
def check_page_title(page, title):
    assert page.title() == title
