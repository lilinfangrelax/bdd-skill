"""
由 api_steps_to_bdd_project.py 生成：通用 API BDD 步骤（读取 fixture）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import requests
from pytest_bdd import given, parsers, then, when

# 相对 bdd_project 包根：steps/api -> bdd_project
_BDD_ROOT = Path(__file__).resolve().parent.parent.parent
_FIXTURE_PATH = _BDD_ROOT / "fixtures/api_steps/task_api.json"


def _load_fixture() -> dict[str, Any]:
    raw = _FIXTURE_PATH.read_text(encoding="utf-8")
    return json.loads(raw)


_FIXTURE: dict[str, Any] | None = None


def _get_fixture() -> dict[str, Any]:
    global _FIXTURE
    if _FIXTURE is None:
        _FIXTURE = _load_fixture()
    return _FIXTURE


def _step_by_label(step_label: str) -> dict[str, Any]:
    for s in _get_fixture()["steps"]:
        if s.get("step_label") == step_label:
            return s
    raise KeyError(f"fixture 中无步骤「{step_label}」")


_CTX_PLACEHOLDER = re.compile(r"\{\{ctx\.(\w+)\}\}")


def _substitute_ctx(obj: Any, ctx: dict[str, Any]) -> Any:
    if isinstance(obj, dict):
        return {k: _substitute_ctx(v, ctx) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_ctx(x, ctx) for x in obj]
    if isinstance(obj, str):

        def repl(m: re.Match[str]) -> str:
            key = m.group(1)
            if key not in ctx:
                raise KeyError(f"ctx 缺少变量: {key}")
            return str(ctx[key])

        return _CTX_PLACEHOLDER.sub(repl, obj)
    return obj


def _get_id_from_response(d: dict[str, Any]) -> str | None:
    if "id" in d and isinstance(d["id"], str):
        return d["id"]
    t = d.get("task")
    if isinstance(t, dict) and isinstance(t.get("id"), str):
        return t["id"]
    data = d.get("data")
    if isinstance(data, dict) and isinstance(data.get("id"), str):
        return data["id"]
    return None


def _extract_id_from_response_json(data: dict[str, Any], _var_hint: str) -> str | None:
    return _get_id_from_response(data)


@pytest.fixture
def api_ctx() -> dict[str, Any]:
    """跨 Step 保存动态值（如 task_id）。"""
    return {}


@given("API 服务正常运行")
def api_service_ok():
    """占位：可扩展为健康检查。"""
    pass


@when(parsers.parse("客户端发送 API 请求「{step_label}」"))
def api_send_request(
    api_ctx: dict[str, Any],
    api_client: requests.Session,
    api_base_url: str,
    step_label: str,
):
    step = _step_by_label(step_label)
    method = step["method"].upper()
    path = step["path"]
    url = api_base_url.rstrip("/") + path
    body = step.get("request_body_template")
    payload = _substitute_ctx(body, api_ctx) if body is not None else None

    if method == "GET":
        resp = api_client.get(url)
    elif method == "POST":
        resp = api_client.post(url, json=payload)
    elif method == "PUT":
        resp = api_client.put(url, json=payload)
    elif method == "DELETE":
        resp = api_client.delete(url, json=payload)
    else:
        raise NotImplementedError(method)

    api_ctx["_last_response"] = resp
    api_ctx["_last_step"] = step

    if not step.get("expect_fail") and step.get("ctx_extract_var") and resp.content:
        try:
            j = resp.json()
            if isinstance(j, dict):
                vid = _extract_id_from_response_json(j, step["ctx_extract_var"])
                if vid:
                    api_ctx[step["ctx_extract_var"]] = vid
        except Exception:
            pass


@then(parsers.parse("API「{step_label}」响应与模板匹配"))
def api_assert_response(api_ctx: dict[str, Any], step_label: str):
    step = _step_by_label(step_label)
    resp: requests.Response = api_ctx["_last_response"]
    expect_fail = step.get("expect_fail", False)
    status_exp = int(step.get("status_expected", 200))

    if expect_fail:
        assert resp.status_code < 200 or resp.status_code >= 300, (
            f"期望失败步骤却返回 2xx: {resp.status_code}"
        )
        return

    assert resp.status_code == status_exp, f"HTTP {resp.status_code} != {status_exp}"

    tmpl = step.get("response_body_template")
    if tmpl is None:
        return
    actual = resp.json()
    expected = _substitute_ctx(tmpl, api_ctx)
    assert actual == expected, f"响应体不一致:\n实际: {actual}\n期望: {expected}"
