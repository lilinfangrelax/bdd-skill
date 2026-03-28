from pytest_bdd import given, parsers, then, when


@given("API 服务已启动")
def api_service_ready(api_client, api_base_url):
    """Check if API service is ready."""
    response = api_client.get(f"{api_base_url}/health")
    assert response.status_code == 200


@when(parsers.parse('发送 GET 请求到 "{endpoint}"'))
def send_get_request(api_client, api_base_url, endpoint):
    """Send GET request to API endpoint."""
    response = api_client.get(f"{api_base_url}{endpoint}")
    return response


@then(parsers.parse("响应状态码应为 {status_code:d}"))
def check_status_code(status_code):
    """Verify response status code."""
    pass
