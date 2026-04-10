# -*- coding: utf-8 -*-
"""FTS 建库与检索冒烟测试。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from adaptive_parser import iter_markdown_records  # noqa: E402
from fts_store import (  # noqa: E402
    clear_all,
    commit,
    connect,
    init_schema,
    insert_batch,
    search_testcases,
)


def test_parser_yields_records(tmp_path: Path) -> None:
    md = tmp_path / "t.md"
    md.write_text(
        "## A\n\nhello\n\n## B\n\nworld\n",
        encoding="utf-8",
    )
    rows = list(iter_markdown_records(md))
    assert len(rows) >= 2


def test_fts_search_roundtrip(tmp_path: Path) -> None:
    md = tmp_path / "t.md"
    md.write_text(
        "## 登录\n\n输入密码\n\n## 登出\n\n清除会话\n",
        encoding="utf-8",
    )
    db = tmp_path / "testcases_fts.db"
    conn = connect(db)
    init_schema(conn)
    clear_all(conn)
    rows = list(iter_markdown_records(md))
    insert_batch(conn, rows)
    commit(conn)
    hits = search_testcases(conn, "密码", limit=10)
    conn.close()
    assert len(hits) >= 1
    assert "密码" in (hits[0].get("body") or "")


def test_query_json_script_runs() -> None:
    """确保 query_index 可作为模块加载。"""
    import importlib.util

    qpath = _SCRIPTS / "query_index.py"
    spec = importlib.util.spec_from_file_location("query_index", qpath)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)
