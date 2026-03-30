# -*- coding: utf-8 -*-
"""
对已构建的 FTS5 数据库执行关键词检索。

用法:
  python query_index.py --db ./fts_out/testcases_fts.db --query "登录 失败"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from fts_store import connect, init_schema, search_testcases  # noqa: E402


def _format_markdown(rows: list[dict]) -> str:
    lines: list[str] = []
    for i, r in enumerate(rows, 1):
        lines.append(f"### 结果 {i}: {r.get('title', '')}")
        lines.append(f"- **文件**: `{r.get('file_path', '')}`")
        lines.append(f"- **行号**: {r.get('start_line', 0)}–{r.get('end_line', 0)}")
        lines.append(f"- **段落**: {r.get('section', '')}")
        lines.append("")
        lines.append("**摘要**")
        lines.append("")
        lines.append(r.get("body_snippet") or r.get("body", "")[:500])
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines).strip()


def main() -> int:
    p = argparse.ArgumentParser(description="FTS5 关键词检索")
    p.add_argument("--db", "-d", required=True, type=Path, help="testcases_fts.db 路径")
    p.add_argument("--query", "-q", required=True, help="检索关键词（支持空格多关键词 AND）")
    p.add_argument("--top-k", "-k", type=int, default=30, help="最多返回条数")
    p.add_argument(
        "--format",
        "-f",
        choices=("json", "markdown"),
        default="markdown",
        help="输出格式",
    )
    args = p.parse_args()

    db_path = args.db.resolve()
    if not db_path.is_file():
        print(f"错误：找不到数据库 {db_path}", file=sys.stderr)
        return 1

    conn = connect(db_path)
    init_schema(conn)
    rows = search_testcases(conn, args.query, limit=args.top_k)
    conn.close()

    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(_format_markdown(rows))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
