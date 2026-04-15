"""通用 API 步骤定义。"""

import jmespath
from pytest_bdd import given, parsers, then, when


def _save_response(scenario_state: dict, response):
    scenario_state["response"] = response
    try:
        scenario_state["response_json"] = response.json()
    except Exception:
        scenario_state["response_json"] = {}


@given(parsers.parse('变量 "{key}" 为 "{value}"'))
def step_set_var(scenario_state, key, value):
    scenario_state["vars"][key] = value


@given(parsers.parse('从全局变量继承 "{key}"'))
def step_inherit_global(scenario_state, global_vars, key):
    scenario_state["vars"][key] = global_vars[key]


@given(parsers.parse('设置请求头 "{header}" 为 "{value}"'))
def step_set_header(http_client, header, value):
    http_client.session.headers[header] = value


@given("使用 token 鉴权")
def step_use_token_auth(http_client, scenario_state, global_vars):
    token = scenario_state["vars"].get("token") or global_vars.get("token")
    assert token, "未找到 token，请先完成登录步骤"
    http_client.set_auth_token(token)


@when(parsers.parse('发送 {method} 请求到 "{path}"'))
def step_send_request(api_service, scenario_state, method, path):
    response, _ = api_service.call(method=method, path=path)
    _save_response(scenario_state, response)


@when(parsers.parse('发送 {method} 请求到 "{path}" 使用模板 "{template}"'))
def step_send_request_with_template(api_service, scenario_state, method, path, template):
    response, _ = api_service.call(
        method=method,
        path=path,
        template=template,
        variables=scenario_state["vars"],
    )
    _save_response(scenario_state, response)


@when(parsers.parse('发送 {method} 请求到 "{path}" 并设置查询参数 "{key}" 为 "{value}"'))
def step_send_request_with_query(api_service, scenario_state, method, path, key, value):
    response, _ = api_service.call(method=method, path=path, params={key: value})
    _save_response(scenario_state, response)


@then(parsers.parse("响应状态码为 {status_code:d}"))
def step_check_status_code(scenario_state, status_code):
    response = scenario_state["response"]
    assert response is not None, "当前场景尚未发送请求"
    assert response.status_code == status_code, (
        f"期望状态码 {status_code}，实际 {response.status_code}\n响应体: {response.text[:300]}"
    )


@then(parsers.parse('响应体字段 "{expression}" 等于 "{expected_value}"'))
def step_check_field_equals(scenario_state, expression, expected_value):
    actual = jmespath.search(expression, scenario_state["response_json"])
    assert str(actual) == expected_value, (
        f"断言失败: '{expression}' 期望 '{expected_value}'，实际 '{actual}'"
    )


@then(parsers.parse('响应体字段 "{expression}" 不为空'))
def step_check_field_not_empty(scenario_state, expression):
    actual = jmespath.search(expression, scenario_state["response_json"])
    assert actual not in (None, "", []), f"断言失败: '{expression}' 为空"


@then(parsers.parse('响应体字段 "{expression}" 大于 {expected_value:d}'))
def step_check_field_greater_than(scenario_state, expression, expected_value):
    actual = jmespath.search(expression, scenario_state["response_json"])
    assert actual is not None, f"断言失败: '{expression}' 未找到"
    assert float(actual) > expected_value, (
        f"断言失败: '{expression}' 期望大于 {expected_value}，实际 {actual}"
    )


@then(parsers.parse('提取变量 "{var_name}" 从响应字段 "{expression}"'))
def step_extract_var(scenario_state, var_name, expression):
    value = jmespath.search(expression, scenario_state["response_json"])
    assert value is not None, f"提取失败: '{expression}' 未找到"
    scenario_state["vars"][var_name] = value
