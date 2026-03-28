"""
本地静态页 + 简易 JSON 接口，用于验证「点击 → 出现 API 请求」。

运行（项目根目录）::

    .\\.venv\\Scripts\\python demo/trace_click_api/server.py

浏览器打开 http://127.0.0.1:8765/ ，点击按钮后可在 Network 或 Playwright Trace 中看到对 /api/ping 的请求。
"""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# 本 demo 静态文件目录
DEMO_ROOT = Path(__file__).resolve().parent


class DemoHandler(SimpleHTTPRequestHandler):
    """提供 index.html 与 /api/ping JSON 接口。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DEMO_ROOT), **kwargs)

    def do_GET(self) -> None:  # noqa: N802 — http.server 沿用库方法名
        if self.path.split("?", 1)[0].rstrip("/") == "/api/ping":
            body = json.dumps(
                {"message": "pong", "demo": "trace_click_api"},
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, format: str, *args) -> None:  # noqa: A003 — 与基类签名一致
        # 简化控制台日志，便于本地调试时看清每次点击对应的请求
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
