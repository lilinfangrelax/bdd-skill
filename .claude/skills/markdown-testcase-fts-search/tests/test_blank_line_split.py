# -*- coding: utf-8 -*-
"""连续空行切段为独立「用例」块。"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from adaptive_parser import ParserConfig, iter_markdown_records  # noqa: E402


def test_double_blank_splits_plain_text_cases(tmp_path: Path) -> None:
    """无标题时，两段正文中间两个空行 → 至少两条记录。"""
    p = tmp_path / "plain.md"
    p.write_text(
        "第一条用例内容 A\nline2\n\n\n"
        "第二条用例内容 B\nline2\n",
        encoding="utf-8",
    )
    recs = list(iter_markdown_records(p))
    assert len(recs) >= 2
    titles_or_bodies = " ".join(r.get("body", "") + r.get("title", "") for r in recs)
    assert "第一条" in titles_or_bodies
    assert "第二条" in titles_or_bodies


def test_double_blank_disabled_single_record(tmp_path: Path) -> None:
    p = tmp_path / "plain.md"
    p.write_text(
        "第一段\n\n\n第二段\n",
        encoding="utf-8",
    )
    cfg = ParserConfig(split_on_consecutive_blank_lines=False)
    recs = list(iter_markdown_records(p, config=cfg))
    assert len(recs) == 1
