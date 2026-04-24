from behave import given, when, then


@given("我打开浏览器")
def open_browser(context):
    # Browser/page are created in environment hooks.
    assert context.page is not None


@when('我导航到 "{url}"')
def navigate_to(context, url):
    context.page.goto(url)


@when('我等待 "{seconds}" 秒')
def wait_seconds(context, seconds):
    timeout_ms = int(float(seconds) * 1000)
    context.page.wait_for_timeout(timeout_ms)


@when("我滚动页面到底部再回到顶部")
def scroll_page_down_and_up(context):
    context.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    context.page.wait_for_timeout(800)
    context.page.evaluate("window.scrollTo(0, 0)")
    context.page.wait_for_timeout(800)


@when("我打开用于触发请求的测试页面")
def open_request_test_page(context):
    context.page.set_content(
        """
        <html>
          <head><title>Request Trigger Demo</title></head>
          <body>
            <h1>Request Trigger Demo</h1>
            <button id="trigger-btn">Send Request</button>
            <script>
              document.getElementById('trigger-btn').addEventListener('click', async () => {
                await fetch('https://httpbin.org/get?from=behave-playwright-demo');
              });
            </script>
          </body>
        </html>
        """
    )
    context.page.wait_for_timeout(1000)


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
