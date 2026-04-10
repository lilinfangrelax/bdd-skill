# -*- coding: utf-8 -*-
"""
验证「少量 ## 模块 + 大量 ### 用例」平台导出结构下，分段条数与用例数一致。

旧逻辑仅看文首多个 ## 会选 H2，导致数千 ### 被合并成少量记录。
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from adaptive_parser import iter_markdown_records  # noqa: E402


def test_many_h3_under_few_h2_one_record_per_case(tmp_path: Path) -> None:
    """3 个模块 × 120 条 ### 用例 → 至少 360 条索引记录（另可有文首块）。"""
    parts: list[str] = ["# 平台导出\n\n", "说明文字若干。\n\n"]
    for mod in range(3):
        parts.append(f"## 模块 M{mod}\n\n")
        for i in range(120):
            parts.append(f"### TC-{mod}-{i:04d} 标题\n\n步骤一行\n期望一行\n\n")
    p = tmp_path / "export.md"
    p.write_text("".join(parts), encoding="utf-8")

    recs = list(iter_markdown_records(p))
    assert len(recs) >= 360, f"期望至少 360 条，实际 {len(recs)}"


def test_h4_dominant_export(tmp_path: Path) -> None:
    """#### 远多于 ### / ## 时按 #### 切段。"""
    parts: list[str] = ["# Doc\n\n"]
    parts.append("## 仅一个模块\n\n")
    for i in range(50):
        parts.append(f"#### CASE-{i:04d}\n\nbody {i}\n\n")
    p = tmp_path / "h4.md"
    p.write_text("".join(parts), encoding="utf-8")
    recs = list(iter_markdown_records(p))
    assert len(recs) >= 50
