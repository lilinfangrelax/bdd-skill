"""
api_steps_to_bdd_project.py
将 api_steps.md 解析为 bdd_project 可用的 fixture JSON，并追加 Feature Scenario、生成 generated_api_steps.py。

用法:
  python api_steps_to_bdd_project.py <api_steps.md> <bdd_project_root> [选项]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

# ── 正则 ───────────────────────────────────────────────────────
# 二级标题二选一：
# - 旧：`## Step 2：新增任务`（数字仅兼容解析，不作为标识）
# - 新：`## 新增任务`（推荐，标识即标题文案 step_label）

_STEP_HEADER_LEGACY = re.compile(r"^##\s+Step\s+\d+\s*[：:]\s*(.+?)\s*$")
_STEP_HEADER_PLAIN = re.compile(r"^##\s+(.+?)\s*$")
_METHOD_URL = re.compile(r"^\*\*(\w+)\*\*\s+`([^`]+)`")
_CTX_SAVE = re.compile(r"💾.*→\s*存入\s*`ctx\.(\w+)`")


def parse_step_heading(line: str) -> Optional[str]:
    """从 `## ...` 行解析 step_label；无法识别则返回 None。"""
    m = _STEP_HEADER_LEGACY.match(line)
    if m:
        return m.group(1).strip()
    m = _STEP_HEADER_PLAIN.match(line)
    if m:
        return m.group(1).strip()
    return None


@dataclass
class ParsedStep:
    step_label: str
    method: str
    url: str
    path: str
    request_body: Optional[dict[str, Any]] = None
    response_body: Optional[dict[str, Any]] = None
    expect_fail: bool = False
    ctx_extract_var: Optional[str] = None
    status_expected: int = 200
    raw_response_block: str = ""


def _extract_path(url: str) -> str:
    p = urlparse(url)
    path = p.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    return path


def _parse_json_block(text: str) -> tuple[Optional[dict[str, Any]], bool, str]:
    """
    解析 Response 代码块。
    返回 (dict | None, expect_fail, raw)。
    """
    raw = text.strip()
    if not raw:
        return None, True, raw

    if re.search(r"status:\s*err", raw, re.I):
        return None, True, raw

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data, False, raw
        return None, True, raw
    except json.JSONDecodeError:
        pass

    lines = [ln for ln in raw.splitlines() if not re.match(r"^\s*//", ln)]
    stripped = "\n".join(lines).strip()
    if not stripped:
        return None, True, raw
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data, False, raw
    except json.JSONDecodeError:
        pass

    return None, True, raw


def _read_fenced_block(lines: list[str], fence_line_idx: int) -> tuple[str, int]:
    """从含 ``` 的行之后读到闭合 ```，返回内容与下一行索引。"""
    i = fence_line_idx + 1
    buf: list[str] = []
    while i < len(lines):
        if lines[i].strip().startswith("```"):
            return "\n".join(buf), i + 1
        buf.append(lines[i])
        i += 1
    return "\n".join(buf), i


def _infer_status_expected(s: ParsedStep) -> int:
    """非 err 步骤：create 类路径默认 201，其余 200。"""
    if s.expect_fail:
        return 200
    pl = s.path.lower()
    if "create" in pl and s.method.upper() == "POST":
        return 201
    return 200


def parse_api_steps_md(md_path: Path) -> list[ParsedStep]:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    steps: list[ParsedStep] = []
    i = 0

    while i < len(lines):
        step_label = parse_step_heading(lines[i])
        if not step_label:
            i += 1
            continue

        i += 1
        method, url = "GET", ""

        while i < len(lines):
            mm = _METHOD_URL.match(lines[i])
            if mm:
                method = mm.group(1).upper()
                url = mm.group(2).strip()
                i += 1
                break
            if parse_step_heading(lines[i]):
                break
            i += 1

        path = _extract_path(url) if url else "/"
        req_body: Optional[dict[str, Any]] = None
        resp_body: Optional[dict[str, Any]] = None
        expect_fail = False
        raw_resp = ""
        ctx_var: Optional[str] = None

        while i < len(lines):
            if parse_step_heading(lines[i]):
                break
            if lines[i].strip() == "---":
                i += 1
                break

            if lines[i].strip() == "**Request**":
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    i += 1
                if i < len(lines) and lines[i].strip().startswith("```"):
                    block, i = _read_fenced_block(lines, i)
                    try:
                        req_body = json.loads(block) if block.strip() else None
                    except json.JSONDecodeError:
                        # 注释行（如 // TODO）不是合法 JSON，去除后重试
                        stripped = "\n".join(
                            ln for ln in block.splitlines() if not re.match(r"^\s*//", ln)
                        ).strip()
                        if stripped:
                            try:
                                req_body = json.loads(stripped)
                            except json.JSONDecodeError as e2:
                                raise ValueError(
                                    f"「{step_label}」Request JSON 无效: {e2}"
                                ) from e2
                        else:
                            req_body = None
                continue

            if lines[i].strip() == "**Response**":
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    i += 1
                if i < len(lines) and lines[i].strip().startswith("```"):
                    block, i = _read_fenced_block(lines, i)
                    raw_resp = block
                    resp_body, ef, _ = _parse_json_block(block)
                    expect_fail = ef
                continue

            if _CTX_SAVE.search(lines[i]):
                ctx_var = _CTX_SAVE.search(lines[i]).group(1)
            i += 1

        ps = ParsedStep(
            step_label=step_label,
            method=method,
            url=url,
            path=path,
            request_body=req_body,
            response_body=resp_body,
            expect_fail=expect_fail,
            ctx_extract_var=ctx_var,
            status_expected=200,
            raw_response_block=raw_resp,
        )
        ps.status_expected = _infer_status_expected(ps)
        steps.append(ps)

    return steps


def _get_id_from_response(d: dict[str, Any]) -> Optional[str]:
    if "id" in d and isinstance(d["id"], str):
        return d["id"]
    t = d.get("task")
    if isinstance(t, dict) and isinstance(t.get("id"), str):
        return t["id"]
    data = d.get("data")
    if isinstance(data, dict) and isinstance(data.get("id"), str):
        return data["id"]
    return None


def _replace_uuid_in_obj(obj: Any, old: str, placeholder: str) -> Any:
    if isinstance(obj, dict):
        return {k: _replace_uuid_in_obj(v, old, placeholder) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_uuid_in_obj(x, old, placeholder) for x in obj]
    if isinstance(obj, str) and obj == old:
        return placeholder
    return obj


def normalize_producer_id(steps: list[ParsedStep]) -> None:
    """将生产者响应中的真实 id 在后续响应模板中替换为 {{ctx.<var>}}。"""
    producer_id: Optional[str] = None
    ctx_name: Optional[str] = None

    for s in steps:
        if s.ctx_extract_var and s.response_body and not s.expect_fail:
            producer_id = _get_id_from_response(s.response_body)
            ctx_name = s.ctx_extract_var
            break

    if not producer_id or not ctx_name:
        return

    ph = f"{{{{ctx.{ctx_name}}}}}"
    for s in steps:
        if s.response_body and isinstance(s.response_body, dict):
            s.response_body = _replace_uuid_in_obj(s.response_body, producer_id, ph)


def build_fixture_dict(steps: list[ParsedStep]) -> dict[str, Any]:
    normalize_producer_id(steps)
    entries = []
    for s in steps:
        entries.append(
            {
                "step_label": s.step_label,
                "method": s.method,
                "url": s.url,
                "path": s.path,
                "request_body_template": s.request_body,
                "response_body_template": s.response_body,
                "expect_fail": s.expect_fail,
                "ctx_extract_var": s.ctx_extract_var,
                "status_expected": s.status_expected,
            }
        )
    return {"version": 2, "steps": entries}


def render_feature_scenario(steps: list[ParsedStep], scenario_name: str) -> str:
    lines = [
        f"  Scenario: {scenario_name}",
        "    Given API 服务正常运行",
    ]
    for s in steps:
        # 使用二级标题文案作为步骤名（与 fixture 中 step_label 一致）
        lines.append(f'    When 客户端发送 API 请求「{s.step_label}」')
        lines.append(f'    Then API「{s.step_label}」响应与模板匹配')
    lines.append("")
    return "\n".join(lines)


def upsert_feature_scenario(feature_path: Path, scenario_block: str, scenario_name: str) -> None:
    """在 feature 中插入或替换指定 Scenario。"""
    text = feature_path.read_text(encoding="utf-8") if feature_path.exists() else ""
    marker = f"  Scenario: {scenario_name}"

    if marker in text:
        pattern = re.compile(
            rf"\n  Scenario: {re.escape(scenario_name)}\n.*?(?=\n  Scenario:|\Z)",
            re.DOTALL,
        )
        new_text, n = pattern.subn("\n" + scenario_block.rstrip("\n"), text, count=1)
        if n:
            feature_path.write_text(new_text.rstrip() + "\n", encoding="utf-8")
            return
        raise RuntimeError(f"无法替换 Scenario: {scenario_name}")

    # 追加到文件末尾（Scenario 之间空一行）
    if text and not text.endswith("\n"):
        text += "\n"
    text = text.rstrip() + "\n\n" + scenario_block
    feature_path.write_text(text, encoding="utf-8")


GENERATED_STEPS_TEMPLATE = r'''"""
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
_FIXTURE_PATH = _BDD_ROOT / "__FIXTURE_REL__"


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
'''


def write_generated_steps(out_path: Path, fixture_rel: str) -> None:
    """fixture_rel 使用正斜杠，相对 bdd_project 根目录。"""
    rel = fixture_rel.replace("\\", "/")
    content = GENERATED_STEPS_TEMPLATE.replace("__FIXTURE_REL__", rel)
    out_path.write_text(content, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="api_steps.md → bdd_project fixture / feature / steps")
    ap.add_argument("api_steps_md", type=Path, help="api_steps.md 路径")
    ap.add_argument("bdd_project_root", type=Path, help="bdd_project 根目录")
    ap.add_argument(
        "--feature",
        type=Path,
        default=None,
        help="Feature 文件路径（默认 bdd_project_root/features/task.feature）",
    )
    ap.add_argument(
        "--scenario-name",
        default="用户完整操作任务（API）",
        help="生成的 Scenario 名称",
    )
    ap.add_argument(
        "--fixture-out",
        type=Path,
        default=None,
        help="fixture JSON 输出路径（默认 bdd_project_root/fixtures/api_steps/task_api.json）",
    )
    ap.add_argument(
        "--steps-out",
        type=Path,
        default=None,
        help="generated_api_steps.py 输出路径（默认 bdd_project_root/steps/api/generated_api_steps.py）",
    )
    args = ap.parse_args()

    root: Path = args.bdd_project_root.resolve()
    md_path = args.api_steps_md.resolve()

    feature_path = (args.feature or (root / "features" / "task.feature")).resolve()
    fixture_path = (args.fixture_out or (root / "fixtures" / "api_steps" / "task_api.json")).resolve()
    steps_path = (args.steps_out or (root / "steps" / "api" / "generated_api_steps.py")).resolve()

    steps = parse_api_steps_md(md_path)
    if not steps:
        print("未解析到任何 Step，请检查 api_steps.md 格式。", file=sys.stderr)
        return 1

    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_dict = build_fixture_dict(steps)
    fixture_path.write_text(
        json.dumps(fixture_dict, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    scenario_block = render_feature_scenario(steps, args.scenario_name)
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    upsert_feature_scenario(feature_path, scenario_block, args.scenario_name)

    try:
        rel_for_steps = fixture_path.relative_to(root).as_posix()
    except ValueError:
        rel_for_steps = fixture_path.name

    steps_path.parent.mkdir(parents=True, exist_ok=True)
    write_generated_steps(steps_path, rel_for_steps)

    print(f"已写入 fixture: {fixture_path}")
    print(f"已更新 feature: {feature_path}")
    print(f"已写入 steps: {steps_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
