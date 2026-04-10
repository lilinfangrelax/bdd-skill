"""
trace_to_bdd.py
将 Playwright 录制脚本（含注释）+ trace 解析 JSON 合并，
输出 BDD step ↔ 接口请求 的 Markdown 报告。
"""

import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── 数据结构 ──────────────────────────────────────────────────

@dataclass
class ApiCall:
    method: str
    url: str
    path: str
    status: int
    network_index: int


@dataclass
class TraceAction:
    index: int
    api_name: str
    method: str
    params: dict
    requests: list[ApiCall]


@dataclass
class BddStep:
    label: str          # 来自 # 注释
    actions: list[TraceAction] = field(default_factory=list)

    @property
    def api_calls(self) -> list[ApiCall]:
        return [r for a in self.actions for r in a.requests]


# ── 解析 py 脚本 ──────────────────────────────────────────────

# 识别 Playwright page.* / context.* 调用的正则（同行不算注释）
_PW_CALL = re.compile(r"^\s*(page|context|browser)\.\w+\(")
# 识别 BDD 注释：# 开头，非分隔线
_COMMENT = re.compile(r"^\s*#(?!-+\s*$)\s+(.+)")
_SEP = re.compile(r"^\s*#\s*-{3,}")


def parse_py(py_path: Path) -> list[BddStep]:
    """
    扫描 py 脚本，按 # 注释 将 playwright 调用分组。
    page.goto 前无注释时，归入「打开页面」默认步骤。
    """
    lines = py_path.read_text(encoding="utf-8").splitlines()

    steps: list[BddStep] = []
    current_label: Optional[str] = None
    pending_calls: int = 0          # 尚未分配步骤的 playwright 调用数
    goto_calls: int = 0             # goto 前的调用（归入隐式步骤）

    for line in lines:
        if _SEP.match(line):
            continue
        m = _COMMENT.match(line)
        if m:
            # 若之前有未归组的 playwright 调用，先建一个隐式步骤
            if pending_calls > 0 and current_label is None:
                steps.append(BddStep(label="打开页面", actions=[]))
                goto_calls = pending_calls
            current_label = m.group(1).strip()
            steps.append(BddStep(label=current_label))
            pending_calls = 0
            continue

        if _PW_CALL.match(line):
            pending_calls += 1
            if current_label is None:
                pass  # 计入 goto_calls 暂存
            # 只统计，实际动作由 action_index 对齐（见下方）

    return steps, goto_calls


# ── 加载 trace JSON ───────────────────────────────────────────

def load_trace_json(json_path: Path) -> list[TraceAction]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    result = []
    for a in data["actions"]:
        reqs = [
            ApiCall(
                method=r["method"],
                url=r["url"],
                path=r["url"].split("://", 1)[-1].split("/", 1)[-1] if "/" in r["url"] else r["url"],
                status=r["status"],
                network_index=r["network_index"],
            )
            for r in a.get("matched_requests", [])
        ]
        result.append(TraceAction(
            index=a["index"],
            api_name=a["api_name"],
            method=a["method"],
            params=a.get("params", {}),
            requests=reqs,
        ))
    return result


# ── 分配 actions → steps ──────────────────────────────────────

def _friendly(action: TraceAction) -> str:
    """把 trace action 转成可读描述。"""
    p = action.params
    selector = p.get("selector", "")
    # 从 internal:role= 或 internal:label= 提取名字
    m = re.search(r'\[name="([^"]+)"', selector)
    label = m.group(1) if m else selector[:40]
    value = p.get("value", "") or (
        p.get("options", [{}])[0].get("valueOrLabel", "") if "options" in p else ""
    )
    url = p.get("url", "")

    if action.method == "goto":
        return f"`goto` → {url}"
    if action.method == "fill":
        return f"`fill` **{label}** = `{value}`"
    if action.method == "click":
        return f"`click` **{label}**"
    if action.method == "selectOption":
        return f"`select` **{label}** = `{value}`"
    return f"`{action.method}` {label}"


def assign_actions(
    steps_raw: list[BddStep],
    goto_calls: int,
    actions: list[TraceAction],
) -> list[BddStep]:
    """
    按顺序将 actions 分配给 steps。
    goto 前的 actions（数量 = goto_calls）归入第一个隐式步骤（若有）。
    """
    idx = 0
    result: list[BddStep] = []

    # 如果解析到了隐式「打开页面」步骤
    first_label = steps_raw[0].label if steps_raw else None
    if first_label == "打开页面":
        s = BddStep(label="打开页面")
        s.actions = actions[idx: idx + goto_calls]
        idx += goto_calls
        result.append(s)
        steps_raw = steps_raw[1:]

    # 剩余步骤：贪婪分配直到下一步开始
    # 策略：每个 step 的 action 数 = 该步骤注释下方的 playwright 调用数
    # 由于无法回头重数，这里改为：直接把剩余 actions 均分给剩余 steps（按脚本行数计）
    # 更健壮的方式：重新扫描 py 脚本统计每段的调用数
    remaining = actions[idx:]
    # 使用「每步包含的 pw 调用数」分配（由调用者传入）
    return result, remaining, steps_raw


# ── 重新扫描 py 获取每步调用数 ──────────────────────────────────

def count_calls_per_step(py_path: Path) -> tuple[int, list[tuple[str, int]]]:
    """返回 (goto前调用数, [(step_label, 调用数), ...])"""
    lines = py_path.read_text(encoding="utf-8").splitlines()

    pre_calls = 0
    in_setup = True
    steps: list[tuple[str, int]] = []
    cur_label = None
    cur_count = 0

    for line in lines:
        if _SEP.match(line):
            continue
        m = _COMMENT.match(line)
        if m:
            if in_setup and cur_count > 0:
                pre_calls = cur_count
            elif cur_label is not None:
                steps.append((cur_label, cur_count))
            in_setup = False
            cur_label = m.group(1).strip()
            cur_count = 0
            continue
        if _PW_CALL.match(line):
            cur_count += 1

    if cur_label is not None and cur_count > 0:
        steps.append((cur_label, cur_count))

    return pre_calls, steps


# ── 生成 Markdown ─────────────────────────────────────────────

_STATUS_ICON = {-1: "⚠️", 200: "✅", 201: "✅"}

def _status_icon(s: int) -> str:
    if s == -1: return "⚠️"
    if 200 <= s < 300: return "✅"
    return "❌"

def _method_badge(m: str) -> str:
    return {"GET": "🟦 GET", "POST": "🟨 POST", "DELETE": "🟥 DELETE"}.get(m, m)


def render_markdown(steps: list[BddStep]) -> str:
    lines = ["# BDD Steps 确认"]
    lines.append("")
    lines.append("勾选需要纳入自动化的接口，取消勾选不需要的。")
    lines.append("")

    for i, step in enumerate(steps, 1):
        lines.append(f"## Step {i}：{step.label}")
        lines.append("")
        api_calls = step.api_calls
        if api_calls:
            for r in api_calls:
                st = "err" if r.status == -1 else str(r.status)
                icon = _status_icon(r.status)
                lines.append(f"- [x] `{r.method}` {r.url} → {icon} {st}")
        else:
            lines.append("- *(无接口请求)*")
        lines.append("")

    return "\n".join(lines)


# ── 主流程 ────────────────────────────────────────────────────

def main(py_path: str, json_path: str, out_path: str):
    py_p = Path(py_path)
    json_p = Path(json_path)

    # 1. 统计每个步骤的 playwright 调用数
    pre_calls, step_counts = count_calls_per_step(py_p)

    # 2. 加载 trace actions
    actions = load_trace_json(json_p)

    # 3. 构建 BddStep 列表并分配 actions
    result_steps: list[BddStep] = []
    idx = 0

    # 隐式「打开页面」步骤（goto 前）
    if pre_calls > 0:
        s = BddStep(label="打开页面")
        s.actions = actions[idx: idx + pre_calls]
        idx += pre_calls
        result_steps.append(s)

    # 注释标注的步骤
    for label, count in step_counts:
        s = BddStep(label=label)
        s.actions = actions[idx: idx + count]
        idx += count
        result_steps.append(s)

    # 4. 生成 Markdown
    md = render_markdown(result_steps)
    Path(out_path).write_text(md, encoding="utf-8")
    print(f"✅ 已生成：{out_path}")
    print(md)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python trace_to_bdd.py <recording.py> <trace_parsed.json> <output.md>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
