# -*- coding: utf-8 -*-
"""
生成「测试平台导出」风格的 Markdown：少量 ## 模块 + 大量 ### 用例。

用于复现/验证：旧版仅根据文首标题误判 H2 导致用例条数远少于真实数量。

示例（约 240000 行量级可自行调大参数，输出到本地路径）:

  python generate_platform_export_fixture.py -o D:/tmp/export_240k.md --modules 30 --cases-per-module 2666

说明：每条用例约 3 行（标题 + 步骤 + 期望），30*2666*3 ≈ 239940 行。
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="生成模拟平台导出的 Markdown")
    p.add_argument("--output", "-o", type=Path, required=True, help="输出 .md 路径")
    p.add_argument("--modules", type=int, default=4, help="## 模块数量")
    p.add_argument("--cases-per-module", type=int, default=500, help="每个模块下 ### 用例条数")
    p.add_argument(
        "--body-lines",
        type=int,
        default=2,
        help="每条用例正文行数（不含 ### 标题行）",
    )
    args = p.parse_args()

    lines: list[str] = [
        "# 测试用例导出（模拟）\n\n",
        "本文档由脚本生成，用于验证 FTS 分段逻辑。\n\n",
    ]
    n_cases = 0
    for m in range(args.modules):
        lines.append(f"## 模块 M{m + 1:02d}\n\n")
        for c in range(args.cases_per_module):
            n_cases += 1
            cid = f"TC-{m + 1:02d}-{c + 1:05d}"
            lines.append(f"### {cid} 示例用例标题\n\n")
            for _ in range(args.body_lines):
                lines.append(f"- 步骤或期望行 {n_cases}\n")
            lines.append("\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(lines)
    args.output.write_text(text, encoding="utf-8")

    out_lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    print(
        f"已写入: {args.output}\n"
        f"  约 {out_lines} 行, {n_cases} 条用例（###）, "
        f"{args.modules} 个模块（##）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
