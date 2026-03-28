"""
parse_trace：合成用例 + 可选本地 task_trace.zip 集成验证。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 保证可 import demo/trace_click_api/parse_trace.py
_API_DIR = Path(__file__).resolve().parent.parent
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

import parse_trace as pt  # noqa: E402

_TRACE_ZIP = _API_DIR / "traces" / "task_trace.zip"


def test_correlate_earliest_window_wins() -> None:
    """请求只归入第一个覆盖其时间的动作窗口。"""
    actions = [
        pt.ActionStep(
            0,
            "a",
            "Frame",
            "click",
            {},
            100.0,
            110.0,
            "Frame.click",
        ),
        pt.ActionStep(
            1,
            "b",
            "Frame",
            "click",
            {},
            120.0,
            130.0,
            "Frame.click",
        ),
    ]
    nets = [
        pt.NetworkEvent(0, 105.0, "POST", "http://x/a", 200, "resource"),
    ]
    r = pt.correlate_actions_network(
        actions, nets, lookahead_ms=1000.0, use_next_action_cap=False
    )
    assert len(r["actions"][0]["matched_requests"]) == 1
    assert r["actions"][0]["matched_requests"][0]["url"] == "http://x/a"
    assert r["actions"][1]["matched_requests"] == []


@pytest.mark.skipif(not _TRACE_ZIP.is_file(), reason="本地录制 task_trace.zip 不存在（traces/ 已 gitignore）")
def test_demo_zip_post_api_maps_to_expected_clicks() -> None:
    """与 trace_click_api server 路由一致：四个 POST 对应四个按钮点击。"""
    rep = pt.build_report(_TRACE_ZIP)
    posts: list[tuple[str, str]] = []
    for a in rep["actions"]:
        for m in a["matched_requests"]:
            if m["method"] == "POST" and "/api/tasks/" in m["url"]:
                posts.append((a["params"].get("selector", ""), m["url"]))
    urls = [u for _, u in posts]
    assert "http://127.0.0.1:8765/api/tasks/create" in urls
    assert "http://127.0.0.1:8765/api/tasks/update" in urls
    assert "http://127.0.0.1:8765/api/tasks/delete" in urls
    assert "http://127.0.0.1:8765/api/tasks/purge" in urls

    for sel, url in posts:
        if "create" in url:
            assert "新增任务" in sel and "POST /api/tasks/create" in sel
        if "update" in url:
            assert "保存修改" in sel
        if url.endswith("/api/tasks/delete"):
            assert "假删除" in sel
        if "purge" in url:
            assert "永久删除" in sel


def test_default_constants_documented() -> None:
    assert pt.DEFAULT_LOOKAHEAD_MS > 0
    assert isinstance(pt.DEFAULT_USE_NEXT_ACTION_CAP, bool)
