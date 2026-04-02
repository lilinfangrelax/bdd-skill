"""
基于 fixtures/api_steps/task_api.json 的 API BDD 步骤（调用 TaskApi 方法）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when

from bdd_project.api.task_api import TaskApi

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


def _step_by_label_with_occurrence(context: dict[str, Any], step_label: str) -> dict[str, Any]:
    """
    同名 step_label 在 fixture 中可能重复（如 GET/POST 分别对应同一个文案）。

    为了在不修改 feature 文本的情况下仍可稳定映射，这里按出现顺序选取第 N 条匹配项。
    """

    all_steps = [s for s in _get_fixture()["steps"] if s.get("step_label") == step_label]
    if not all_steps:
        raise KeyError(f"fixture 中无步骤「{step_label}」")

    # 同名 step_label 可能同时包含“查询类”(request_body_template=None)与“写操作”(request_body_template!=None)。
    # 这里优先使用写操作分支，避免把“编辑”误映射成“查询列表”导致断言失配。
    candidate_steps = [s for s in all_steps if s.get("request_body_template") is not None]
    if not candidate_steps:
        candidate_steps = all_steps

    counts = context.setdefault("_step_label_counts", {})
    idx = int(counts.get(step_label, 0))
    counts[step_label] = idx + 1

    if idx >= len(candidate_steps):
        # 超出 fixture 条目时退回到最后一条，避免直接抛错导致中断。
        return candidate_steps[-1]
    return candidate_steps[idx]


_CTX_PLACEHOLDER = re.compile(r"\{\{ctx\.(\w+)\}\}")


def _substitute_ctx(obj: Any, ctx: dict[str, Any]) -> Any:
    """将 {{ctx.xxx}} 替换为 context 里的值。"""

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


@pytest.fixture
def context() -> dict[str, Any]:
    """跨 Step 保存动态值（如 task_id）。"""

    return {}


@given("API 服务正常运行")
def api_service_ok():
    """占位：可扩展为健康检查。"""

    pass


@when(parsers.parse("客户端发送 API 请求「{step_label}」"))
def api_send_request(
    context: dict[str, Any],
    task_api: TaskApi,
    step_label: str,
):
    step = _step_by_label_with_occurrence(context, step_label)
    path = step["path"]
    body_template = step.get("request_body_template")
    payload = _substitute_ctx(body_template, context) if body_template is not None else None

    if path == "/api/tasks/create":
        resp = task_api.create_task(payload)
    elif path == "/api/tasks":
        resp = task_api.list_tasks()
    elif path == "/api/tasks/update":
        resp = task_api.update_task(payload)
    elif path == "/api/tasks/delete":
        resp = task_api.soft_delete_task(payload)
    elif path == "/api/tasks/purge":
        resp = task_api.purge_task(payload)
    else:
        raise NotImplementedError(f"未支持的 path: {path}")

    context["_last_response"] = resp
    context["_last_step"] = step

    if not step.get("expect_fail") and step.get("ctx_extract_var") and resp.content:
        try:
            j = resp.json()
            if isinstance(j, dict):
                vid = _get_id_from_response(j)
                if vid:
                    context[step["ctx_extract_var"]] = vid
        except Exception:
            # 解析失败时保持上下文不变，由后续断言来暴露问题。
            pass


@then(parsers.parse("API「{step_label}」响应与模板匹配"))
def api_assert_response(context: dict[str, Any], step_label: str):
    last_step: dict[str, Any] = context["_last_step"]
    resp = context["_last_response"]
    expect_fail = bool(last_step.get("expect_fail", False))
    status_exp = int(last_step.get("status_expected", 200))

    if expect_fail:
        assert resp.status_code < 200 or resp.status_code >= 300, (
            f"期望失败步骤却返回 2xx: {resp.status_code}"
        )
        return

    assert resp.status_code == status_exp, f"HTTP {resp.status_code} != {status_exp}"

    tmpl = last_step.get("response_body_template")
    if tmpl is None:
        return

    actual = resp.json()
    expected = _substitute_ctx(tmpl, context)

    assert actual == expected, (
        f"响应体不一致(步骤={step_label}):\n实际: {actual}\n期望: {expected}"
    )

