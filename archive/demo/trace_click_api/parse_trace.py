"""
从 Playwright trace.zip 解析 UI 操作与网络请求，并按时间窗口关联。

实际格式（Playwright 1.58+）与部分文档示例不同：
- trace.trace：使用 type=before/after，含 class、method、params；非 type=action。
- trace.network：使用 type=resource-snapshot，HAR 嵌套在 snapshot 下，时间用 _monotonicTime（与 trace 中 startTime 同轴）。
"""

from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 视为「用户级」Frame 操作（用于 UI 步骤列表）
_FRAME_UI_METHODS = frozenset(
    {
        "click",
        "dblclick",
        "fill",
        "goto",
        "hover",
        "press",
        "selectOption",
        "setChecked",
        "setInputFiles",
        "tap",
        "type",
    }
)

# 与 demo 样本扫参后较稳妥的默认关联参数（可在 CLI 中覆盖）
DEFAULT_LOOKAHEAD_MS = 1500.0
DEFAULT_USE_NEXT_ACTION_CAP = True

# 常见静态资源扩展名（小写），命中则默认排除
_STATIC_SUFFIXES = (
    ".js",
    ".mjs",
    ".css",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".map",
)


@dataclass
class ActionStep:
    """一次 UI 调用（before + 对应 after 合并）。"""

    index: int
    call_id: str
    class_name: str
    method: str
    params: dict[str, Any]
    start_time: float
    end_time: float
    api_name: str  # 形如 Frame.click

    def summary_selector(self) -> str | None:
        p = self.params
        s = p.get("selector") or p.get("url")
        return str(s)[:200] if s is not None else None


@dataclass
class NetworkEvent:
    """一条可关联的网络请求。"""

    index: int
    start_time: float
    method: str
    url: str
    status: int | None
    source: str  # resource-snapshot | resource
    raw: dict[str, Any] = field(default_factory=dict)


def _iter_ndjson_lines(data: bytes) -> Iterator[tuple[int, dict[str, Any]]]:
    text = data.decode("utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            yield lineno, json.loads(line)
        except json.JSONDecodeError:
            continue


def _find_member(names: list[str], basename: str) -> str | None:
    for n in names:
        norm = n.replace("\\", "/")
        if norm == basename or norm.endswith("/" + basename):
            return n
    return None


def parse_actions_from_trace_bytes(trace_bytes: bytes) -> tuple[list[ActionStep], list[str]]:
    """解析 trace.trace：合并 before/after，仅保留 Frame 的用户方法。"""
    after_by_call: dict[str, dict[str, Any]] = {}
    diagnostics: list[str] = []
    for lineno, obj in _iter_ndjson_lines(trace_bytes):
        t = obj.get("type")
        if t == "after":
            cid = obj.get("callId")
            if isinstance(cid, str):
                after_by_call[cid] = obj
    steps: list[ActionStep] = []
    index = 0
    for lineno, obj in _iter_ndjson_lines(trace_bytes):
        if obj.get("type") != "before":
            continue
        cls = obj.get("class")
        method = obj.get("method")
        cid = obj.get("callId")
        if cls != "Frame" or not isinstance(method, str) or method not in _FRAME_UI_METHODS:
            continue
        if not isinstance(cid, str):
            continue
        start = obj.get("startTime")
        after = after_by_call.get(cid)
        end = after.get("endTime") if after else None
        if not isinstance(start, (int, float)):
            diagnostics.append(f"before {cid} 缺少 startTime")
            continue
        if not isinstance(end, (int, float)):
            end = float(start)

        params = obj.get("params")
        if not isinstance(params, dict):
            params = {}
        steps.append(
            ActionStep(
                index=index,
                call_id=cid,
                class_name=str(cls),
                method=method,
                params=params,
                start_time=float(start),
                end_time=float(end),
                api_name=f"{cls}.{method}",
            )
        )
        index += 1

    steps.sort(key=lambda s: s.start_time)
    for i, s in enumerate(steps):
        s.index = i
    return steps, diagnostics


def _monotonic_from_snapshot(snap: dict[str, Any]) -> float | None:
    t = snap.get("_monotonicTime")
    if isinstance(t, (int, float)):
        return float(t)
    return None


def _parse_iso_to_utc_ms(iso: str) -> float | None:
    try:
        s = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp() * 1000.0
    except (ValueError, TypeError):
        return None


def parse_network_from_network_bytes(
    network_bytes: bytes,
    *,
    include_document: bool = False,
) -> tuple[list[NetworkEvent], list[str]]:
    """解析 trace.network：支持 resource-snapshot（HAR）与简化的 resource 行。"""
    events: list[NetworkEvent] = []
    diagnostics: list[str] = []
    idx = 0
    for lineno, obj in _iter_ndjson_lines(network_bytes):
        t = obj.get("type")
        if t == "resource-snapshot":
            snap = obj.get("snapshot")
            if not isinstance(snap, dict):
                continue
            req = snap.get("request")
            if not isinstance(req, dict):
                continue
            url = req.get("url")
            method = req.get("method")
            if not isinstance(url, str) or not isinstance(method, str):
                continue
            resp = snap.get("response") if isinstance(snap.get("response"), dict) else {}
            status = resp.get("status")
            st = _monotonic_from_snapshot(snap)
            if st is None:
                iso = snap.get("startedDateTime")
                if isinstance(iso, str):
                    parsed = _parse_iso_to_utc_ms(iso)
                    if parsed is not None:
                        st = parsed
            if st is None:
                diagnostics.append(f"resource-snapshot 行 {lineno} 无可用时间，已跳过")
                continue

            # 静态资源过滤
            path = url.split("?", 1)[0].lower()
            if any(path.endswith(suf) for suf in _STATIC_SUFFIXES):
                continue
            # 主文档 GET（仅导航页）
            if method.upper() == "GET" and not include_document:
                mt = ""
                content = resp.get("content") if isinstance(resp.get("content"), dict) else {}
                if isinstance(content, dict):
                    mt = (content.get("mimeType") or "").lower()
                if mt.startswith("text/html") or path.endswith("/") or path.endswith(".htm"):
                    continue

            events.append(
                NetworkEvent(
                    index=idx,
                    start_time=st,
                    method=method.upper(),
                    url=url,
                    status=int(status) if isinstance(status, int) else None,
                    source="resource-snapshot",
                    raw={"lineno": lineno},
                )
            )
            idx += 1

        elif t == "resource":
            # 文档/旧格式兼容
            url = obj.get("url")
            method = obj.get("method")
            st = obj.get("startTime")
            status = obj.get("status")
            if not isinstance(url, str) or not isinstance(method, str):
                continue
            if not isinstance(st, (int, float)):
                continue
            path = url.split("?", 1)[0].lower()
            if any(path.endswith(suf) for suf in _STATIC_SUFFIXES):
                continue
            events.append(
                NetworkEvent(
                    index=idx,
                    start_time=float(st),
                    method=str(method).upper(),
                    url=url,
                    status=int(status) if isinstance(status, int) else None,
                    source="resource",
                    raw={"lineno": lineno},
                )
            )
            idx += 1

    events.sort(key=lambda e: e.start_time)
    for i, e in enumerate(events):
        e.index = i
    return events, diagnostics


def load_trace_zip(
    zip_path: Path | str,
    *,
    include_document: bool = False,
) -> dict[str, Any]:
    """读取 zip，返回 actions、network_events、diagnostics、meta。"""
    path = Path(zip_path)
    meta: dict[str, Any] = {"zip_path": str(path.resolve())}
    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        trace_name = _find_member(names, "trace.trace")
        network_name = _find_member(names, "trace.network")
        if not trace_name:
            raise ValueError("zip 中未找到 trace.trace")
        if not network_name:
            raise ValueError("zip 中未找到 trace.network")
        meta["trace_entry"] = trace_name
        meta["network_entry"] = network_name
        trace_bytes = zf.read(trace_name)
        network_bytes = zf.read(network_name)

    actions, da = parse_actions_from_trace_bytes(trace_bytes)
    network_events, dn = parse_network_from_network_bytes(
        network_bytes, include_document=include_document
    )
    diagnostics = da + dn
    return {
        "actions": actions,
        "network_events": network_events,
        "diagnostics": diagnostics,
        "meta": meta,
    }


def correlate_actions_network(
    actions: list[ActionStep],
    network_events: list[NetworkEvent],
    *,
    lookahead_ms: float = DEFAULT_LOOKAHEAD_MS,
    use_next_action_cap: bool = DEFAULT_USE_NEXT_ACTION_CAP,
) -> dict[str, Any]:
    """
    时间窗口：[action.start_time, upper]
    upper = min(action.end_time + lookahead_ms, next_action.start_time) 当 use_next_action_cap 为真。
    请求归入第一个满足 lower <= t <= upper 的动作（最早匹配）。
    """
    n = len(actions)
    matched: list[list[dict[str, Any]]] = [[] for _ in range(n)]
    lowers: list[float] = []
    uppers: list[float] = []
    for i, a in enumerate(actions):
        lower = a.start_time
        cap_after = a.end_time + float(lookahead_ms)
        if use_next_action_cap and i + 1 < n:
            upper = min(cap_after, actions[i + 1].start_time)
        else:
            upper = cap_after
        lowers.append(lower)
        uppers.append(upper)

    orphan: list[dict[str, Any]] = []
    for ev in network_events:
        t = ev.start_time
        assigned = -1
        for i in range(n):
            if lowers[i] <= t <= uppers[i]:
                assigned = i
                break
        item = {
            "method": ev.method,
            "url": ev.url,
            "status": ev.status,
            "start_time": ev.start_time,
            "reason": "in_window",
            "network_index": ev.index,
            "source": ev.source,
        }
        if assigned >= 0:
            matched[assigned].append(item)
        else:
            item["reason"] = "no_window"
            orphan.append(item)

    out_actions: list[dict[str, Any]] = []
    for i, a in enumerate(actions):
        out_actions.append(
            {
                "index": a.index,
                "call_id": a.call_id,
                "api_name": a.api_name,
                "method": a.method,
                "params": a.params,
                "start_time": a.start_time,
                "end_time": a.end_time,
                "window": {"lower": lowers[i], "upper": uppers[i]},
                "matched_requests": matched[i],
            }
        )

    return {
        "actions": out_actions,
        "orphan_requests": orphan,
        "params": {
            "lookahead_ms": lookahead_ms,
            "use_next_action_cap": use_next_action_cap,
        },
    }


def build_report(
    zip_path: Path | str,
    *,
    lookahead_ms: float = DEFAULT_LOOKAHEAD_MS,
    use_next_action_cap: bool = DEFAULT_USE_NEXT_ACTION_CAP,
    include_document: bool = False,
) -> dict[str, Any]:
    """完整报告（供 JSON 输出）。"""
    loaded = load_trace_zip(zip_path, include_document=include_document)
    actions = loaded["actions"]
    network_events = loaded["network_events"]
    corr = correlate_actions_network(
        actions,
        network_events,
        lookahead_ms=lookahead_ms,
        use_next_action_cap=use_next_action_cap,
    )
    return {
        "meta": loaded["meta"],
        "diagnostics": loaded["diagnostics"],
        **corr,
    }


def report_to_markdown(report: dict[str, Any]) -> str:
    """简要 Markdown 表。"""
    lines = [
        "# Trace 操作与请求关联",
        "",
        f"- lookahead_ms: {report['params']['lookahead_ms']}",
        f"- use_next_action_cap: {report['params']['use_next_action_cap']}",
        "",
        "## UI 步骤",
        "",
        "| # | api_name | start | end | 关联请求数 |",
        "|---|----------|-------|-----|------------|",
    ]
    for a in report["actions"]:
        nreq = len(a["matched_requests"])
        lines.append(
            f"| {a['index']} | {a['api_name']} | {a['start_time']:.2f} | {a['end_time']:.2f} | {nreq} |"
        )
    lines.extend(["", "## 未匹配请求", ""])
    if not report["orphan_requests"]:
        lines.append("（无）")
    else:
        lines.append("| method | url | time |")
        lines.append("|--------|-----|------|")
        for o in report["orphan_requests"][:50]:
            lines.append(f"| {o['method']} | {o['url'][:80]} | {o['start_time']:.2f} |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="解析 Playwright trace.zip，关联 UI 与网络请求")
    parser.add_argument("--zip", type=Path, required=True, help="trace.zip 路径")
    parser.add_argument(
        "--lookahead",
        type=float,
        default=DEFAULT_LOOKAHEAD_MS,
        help="动作结束后的前瞻毫秒",
    )
    parser.add_argument(
        "--no-next-cap",
        action="store_true",
        help="不用下一操作 start_time 截断窗口上界",
    )
    parser.add_argument(
        "--include-document",
        action="store_true",
        help="包含 text/html 主文档 GET",
    )
    parser.add_argument("--json-out", type=Path, default=None, help="写入 JSON 报告路径")
    parser.add_argument("--markdown-out", type=Path, default=None, help="写入 Markdown 路径")
    args = parser.parse_args()

    report = build_report(
        args.zip,
        lookahead_ms=args.lookahead,
        use_next_action_cap=not args.no_next_cap,
        include_document=args.include_document,
    )
    # JSON 可序列化：actions 已是 dict
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(report_to_markdown(report), encoding="utf-8")
    if not args.json_out and not args.markdown_out:
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
