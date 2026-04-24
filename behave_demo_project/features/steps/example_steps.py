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
    assert title in context.page.title()


@then('验证系统发送了指向 "{target_url_part}" 的接口请求')
def verify_request_sent(context, target_url_part):
    # expect_request will capture the first matching request in this block.
    with context.page.expect_request(
        lambda request: target_url_part in request.url
    ) as first_request:
        # Place the request-triggering action in this block.
        context.page.get_by_role("button").click()

    actual_url = first_request.value.url
    print(f"实际发送的 URL 为: {actual_url}")
    assert target_url_part in actual_url
