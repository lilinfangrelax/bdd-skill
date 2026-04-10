"""
本地静态页 + 任务相关 JSON 接口，用于验证「点击 → 出现 API 请求」。

运行（项目根目录）::

    .\\.venv\\Scripts\\python demo/trace_click_api/server.py

浏览器打开 http://127.0.0.1:8765/ ，在 Network 或 Playwright Trace 中可观察各 POST 请求。
"""

from __future__ import annotations

import argparse
import json
import threading
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# 本 demo 静态文件目录
DEMO_ROOT = Path(__file__).resolve().parent

# 内存任务库（多线程下需加锁）
_tasks_lock = threading.Lock()
_tasks: dict[str, dict[str, Any]] = {}


def _json_response(handler: SimpleHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: SimpleHTTPRequestHandler) -> dict[str, Any] | None:
    length = int(handler.headers.get("Content-Length", 0))
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _task_to_public(t: dict[str, Any]) -> dict[str, Any]:
    """返回给前端的任务字段（不含内部 deleted 以外的敏感字段）。"""
    return {
        "id": t["id"],
        "name": t["name"],
        "start_time": t["start_time"],
        "end_time": t["end_time"],
        "priority": t["priority"],
        "description": t["description"],
        "tags": t["tags"],
        "deleted": t["deleted"],
    }


class DemoHandler(SimpleHTTPRequestHandler):
    """提供 index.html 与任务相关 JSON 接口。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DEMO_ROOT), **kwargs)

    def do_GET(self) -> None:  # noqa: N802 — http.server 沿用库方法名
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path == "/api/tasks":
            with _tasks_lock:
                active = [_task_to_public(t) for t in _tasks.values() if not t["deleted"]]
                soft_deleted = [_task_to_public(t) for t in _tasks.values() if t["deleted"]]
            _json_response(
                self,
                200,
                {"ok": True, "active": active, "soft_deleted": soft_deleted},
            )
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        data = _read_json_body(self)
        if data is None:
            _json_response(self, 400, {"ok": False, "error": "请求体须为 JSON 对象"})
            return

        if path == "/api/tasks/create":
            self._post_create(data)
            return
        if path == "/api/tasks/update":
            self._post_update(data)
            return
        if path == "/api/tasks/delete":
            self._post_soft_delete(data)
            return
        if path == "/api/tasks/purge":
            self._post_purge(data)
            return

        _json_response(self, 404, {"ok": False, "error": "未知的 POST 路径"})

    def _post_create(self, data: dict[str, Any]) -> None:
        name = (data.get("name") or "").strip()
        if not name:
            _json_response(self, 400, {"ok": False, "error": "任务名称不能为空"})
            return
        start_time = (data.get("start_time") or "").strip()
        end_time = (data.get("end_time") or "").strip()
        priority = (data.get("priority") or "中").strip()
        description = (data.get("description") or "").strip()
        tags_raw = data.get("tags")
        if isinstance(tags_raw, list):
            tags = [str(x).strip() for x in tags_raw if str(x).strip()]
        elif isinstance(tags_raw, str):
            tags = [x.strip() for x in tags_raw.split(",") if x.strip()]
        else:
            tags = []

        tid = str(uuid.uuid4())
        record = {
            "id": tid,
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
            "priority": priority,
            "description": description,
            "tags": tags,
            "deleted": False,
        }
        with _tasks_lock:
            _tasks[tid] = record
        _json_response(self, 201, {"ok": True, "task": _task_to_public(record)})

    def _post_update(self, data: dict[str, Any]) -> None:
        tid = data.get("id")
        if not tid or not isinstance(tid, str):
            _json_response(self, 400, {"ok": False, "error": "缺少或非法的 id"})
            return
        with _tasks_lock:
            if tid not in _tasks:
                _json_response(self, 404, {"ok": False, "error": "任务不存在"})
                return
            t = _tasks[tid]
            if t["deleted"]:
                _json_response(self, 400, {"ok": False, "error": "已假删除的任务请先恢复逻辑（本 demo 未实现恢复）或勿修改"})
                return
            if "name" in data:
                name = (data.get("name") or "").strip()
                if not name:
                    _json_response(self, 400, {"ok": False, "error": "任务名称不能为空"})
                    return
                t["name"] = name
            if "start_time" in data:
                t["start_time"] = (data.get("start_time") or "").strip()
            if "end_time" in data:
                t["end_time"] = (data.get("end_time") or "").strip()
            if "priority" in data:
                t["priority"] = (data.get("priority") or "中").strip()
            if "description" in data:
                t["description"] = (data.get("description") or "").strip()
            if "tags" in data:
                tr = data.get("tags")
                if isinstance(tr, list):
                    t["tags"] = [str(x).strip() for x in tr if str(x).strip()]
                elif isinstance(tr, str):
                    t["tags"] = [x.strip() for x in tr.split(",") if x.strip()]
                else:
                    t["tags"] = []
            out = _task_to_public(dict(t))

        _json_response(self, 200, {"ok": True, "task": out})

    def _post_soft_delete(self, data: dict[str, Any]) -> None:
        tid = data.get("id")
        if not tid or not isinstance(tid, str):
            _json_response(self, 400, {"ok": False, "error": "缺少或非法的 id"})
            return
        with _tasks_lock:
            if tid not in _tasks:
                _json_response(self, 404, {"ok": False, "error": "任务不存在"})
                return
            t = _tasks[tid]
            if t["deleted"]:
                _json_response(self, 400, {"ok": False, "error": "任务已是假删除状态"})
                return
            t["deleted"] = True
            out = _task_to_public(dict(t))
        _json_response(self, 200, {"ok": True, "message": "已假删除", "task": out})

    def _post_purge(self, data: dict[str, Any]) -> None:
        tid = data.get("id")
        if not tid or not isinstance(tid, str):
            _json_response(self, 400, {"ok": False, "error": "缺少或非法的 id"})
            return
        with _tasks_lock:
            if tid not in _tasks:
                _json_response(self, 404, {"ok": False, "error": "任务不存在"})
                return
            t = _tasks[tid]
            if not t["deleted"]:
                _json_response(
                    self,
                    400,
                    {"ok": False, "error": "仅允许永久删除已假删除的任务"},
                )
                return
            del _tasks[tid]
        _json_response(self, 200, {"ok": True, "message": "已永久删除", "id": tid})

    def log_message(self, format: str, *args) -> None:  # noqa: A003 — 与基类签名一致
        message = format % args
        print(f"[demo] {message.strip()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="trace_click_api 本地演示服务")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="监听地址，默认 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="端口，默认 8765",
    )
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    print(f"演示页: http://{args.host}:{args.port}/")
    print("按 Ctrl+C 结束")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
