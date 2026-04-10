"""
md_to_api_steps.py
输入：① 用户勾选后的 bdd_confirmed.md  ② 原始 trace.zip
输出：api_steps.md（含真实 request/response body + ctx 依赖标注）

用法：
  python md_to_api_steps.py <bdd_confirmed.md> <trace.zip> <output.md>
"""

import json
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


# ── 数据结构 ──────────────────────────────────────────────────

@dataclass
class ApiEntry:
    method: str
    url: str
    path: str
    status: int
    step_index: int
    step_label: str
    request_body: Optional[dict] = None
    response_body: Optional[dict] = None


# ── Step 1: 解析 MD，提取 [x] 选中项 ─────────────────────────

_STEP_RE = re.compile(r"^##\s+Step\s+(\d+)[：:]\s*(.+)")
_API_RE  = re.compile(r"^\s*-\s*\[(x)\]\s*`(\w+)`\s+(https?://\S+)")

def parse_md(md_path: Path) -> list[ApiEntry]:
    entries: list[ApiEntry] = []
    cur_index, cur_label = 0, ""
    for line in md_path.read_text(encoding="utf-8").splitlines():
        m = _STEP_RE.match(line)
        if m:
            cur_index = int(m.group(1))
            cur_label = m.group(2).strip()
            continue
        m = _API_RE.match(line)
        if m:
            _, method, url = m.groups()
            # 从行尾提取 status（`→ ✅ 200` 或 `→ ⚠️ err`）
            status_m = re.search(r"→\s+\S+\s+(\S+)\s*$", line)
            try:
                status = int(status_m.group(1)) if status_m else -1
            except ValueError:
                status = -1
            entries.append(ApiEntry(
                method=method,
                url=url,
                path=urlparse(url).path,
                status=status,
                step_index=cur_index,
                step_label=cur_label,
            ))
    return entries


# ── Step 2: 从 trace.zip 按 url+method 提取 body ─────────────

def _read_resource(z: zipfile.ZipFile, sha1: str) -> Optional[dict]:
    """读取 resources/<sha1> 文件，尝试解析为 JSON。"""
    name = f"resources/{sha1}"
    if name not in z.namelist():
        return None
    raw = z.read(name).decode("utf-8", errors="replace").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw  # 保留原始文本


def enrich_from_zip(entries: list[ApiEntry], zip_path: Path):
    """
    扫描 trace.network，按 method+url 匹配，
    读取 postData._sha1 和 response.content._sha1 对应的资源文件。
    """
    with zipfile.ZipFile(zip_path) as z:
        # 构建 "METHOD:url" → snapshot 的查找表
        network_entry = next(
            (e for e in z.namelist() if e.endswith(".network")), None
        )
        if not network_entry:
            return

        snapshots: dict[str, dict] = {}
        with z.open(network_entry) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                snap = ev.get("snapshot", {})
                req = snap.get("request", {})
                url = req.get("url", "")
                method = req.get("method", "")
                if url and method:
                    key = f"{method}:{url}"
                    # 保留第一次出现（与 trace 时间顺序一致）
                    snapshots.setdefault(key, snap)

        # 为每个选中接口填充 body
        for entry in entries:
            key = f"{entry.method}:{entry.url}"
            snap = snapshots.get(key)
            if not snap:
                continue

            req  = snap.get("request", {})
            resp = snap.get("response", {})

            # request body
            post = req.get("postData", {})
            sha1_req = post.get("_sha1")
            if sha1_req:
                entry.request_body = _read_resource(z, sha1_req)

            # response body
            sha1_resp = resp.get("content", {}).get("_sha1")
            if sha1_resp:
                entry.response_body = _read_resource(z, sha1_resp)


# ── Step 3: 依赖推断（create → ctx.xxx_id） ──────────────────

def _var_name(path: str) -> str:
    """从路径最后一段推断资源类型，生成变量名。如 /api/tasks/create → task_id"""
    parts = [p for p in path.split("/") if p and p not in ("api", "create", "update", "delete", "purge")]
    resource = parts[-1] if parts else "item"
    # 单数化简单处理
    if resource.endswith("s"):
        resource = resource[:-1]
    return f"{resource}_id"


def infer_ctx(entries: list[ApiEntry]) -> dict[int, str]:
    """
    返回 { entry_index: ctx_var_name }
    表示该 entry 应将响应中的 id 存入 ctx.<var>
    """
    producers: list[tuple[int, str, str]] = []  # (idx, var_name, step_label)
    ctx_map: dict[int, str] = {}

    for i, e in enumerate(entries):
        path_lower = e.path.lower()

        # 识别「创建」类接口
        if "create" in path_lower and e.status in (200, 201):
            var = _var_name(e.path)
            producers.append((i, var, e.step_label))
            ctx_map[i] = var  # 这个 entry 需要提取并存储

    return ctx_map, producers


def apply_ctx(entries: list[ApiEntry], producers: list[tuple[int, str, str]]) -> list[str]:
    """
    对每个 entry 的 request_body，将实际录制中的 id 值替换为 {{ctx.var}} 占位符。
    返回每个 entry 对应的「ctx 注入说明」列表（空字符串表示无需注入）。
    """
    hints = [""] * len(entries)

    for src_i, var, from_label in producers:
        src_entry = entries[src_i]
        # 从 response_body 拿到真实 id 值
        real_id = None
        if isinstance(src_entry.response_body, dict):
            # 尝试常见路径：.id / .task.id / .data.id
            real_id = (
                src_entry.response_body.get("id")
                or (src_entry.response_body.get("task") or {}).get("id")
                or (src_entry.response_body.get("data") or {}).get("id")
            )

        if not real_id:
            continue

        # 替换后续 entry 的 request_body 中的 id 值
        for j in range(src_i + 1, len(entries)):
            body = entries[j].request_body
            if not isinstance(body, dict):
                continue
            if body.get("id") == real_id:
                body["id"] = f"{{{{ctx.{var}}}}}"
                hints[j] = f"来自「{from_label}」→ `ctx.{var}`"

    return hints


# ── Step 4: 渲染 Markdown ─────────────────────────────────────

def _fmt(obj, indent=2) -> str:
    if obj is None:
        return "  // TODO: 补充字段"
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, ensure_ascii=False, indent=indent)

def _status_icon(s: int) -> str:
    if s == -1: return "⚠️"
    if 200 <= s < 300: return "✅"
    return "❌"

def render(entries: list[ApiEntry], ctx_map: dict[int, str], hints: list[str]) -> str:
    lines = ["# API 自动化步骤", ""]
    for i, e in enumerate(entries):
        st = "err" if e.status == -1 else str(e.status)
        lines += [f"## Step {e.step_index}：{e.step_label}", ""]
        lines += [f"**{e.method}** `{e.url}`", ""]

        lines += ["**Request**", "", "```json", _fmt(e.request_body), "```", ""]

        resp_note = ""
        if e.status == -1:
            resp_note = "  // 录制时请求中断，建议重新录制确认响应结构"
        lines += ["**Response**", "", "```json"]
        if e.response_body:
            lines.append(_fmt(e.response_body))
        else:
            lines.append(f"  // status: {st}{resp_note}")
        lines += ["```", ""]

        if i in ctx_map:
            var = ctx_map[i]
            lines.append(f"> 💾 提取 `response` 中的 `id` → 存入 `ctx.{var}`")
            lines.append("")
        if hints[i]:
            lines.append(f"> 🔗 `id` 引用 {hints[i]}")
            lines.append("")

        lines.append("---")
        lines.append("")
    return "\n".join(lines)


# ── 主流程 ────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 4:
        print("用法: python md_to_api_steps.py <bdd_confirmed.md> <trace.zip> <output.md>")
        sys.exit(1)

    md_path   = Path(sys.argv[1])
    zip_path  = Path(sys.argv[2])
    out_path  = Path(sys.argv[3])

    entries = parse_md(md_path)
    if not entries:
        print("⚠️  未找到任何 [x] 选中的接口，请检查 MD 文件格式。")
        sys.exit(1)

    enrich_from_zip(entries, zip_path)
    ctx_map, producers = infer_ctx(entries)
    hints = apply_ctx(entries, producers)

    md = render(entries, ctx_map, hints)
    out_path.write_text(md, encoding="utf-8")
    print(f"✅ 已生成：{out_path}（共 {len(entries)} 个接口）")
    print(md)


if __name__ == "__main__":
    main()
