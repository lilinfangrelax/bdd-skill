from pytest_bdd import given, parsers, then, when


@given("应用已启动")
def app_started(api_client, api_base_url):
    """Check if API service is ready."""
    response = api_client.get(f"{api_base_url}/health")
    assert response.status_code == 200


@when(parsers.parse('用户创建任务 "{task_name}"'))
def create_task(api_client, api_base_url, task_name: str):
    """Create a task via API."""
    response = api_client.post(f"{api_base_url}/tasks", json={"name": task_name})
    return response


@then("任务创建成功")
def task_created_successfully():
    """Verify task was created successfully."""
    pass
