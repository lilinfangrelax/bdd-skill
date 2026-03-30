# -*- coding: utf-8 -*-
"""SQLite FTS5 索引与检索（trigram 分词，适配中文片段）。"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """创建 FTS5 表与元数据表。"""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS testcase_chunks USING fts5(
            uuid UNINDEXED,
            title,
            section,
            body,
            file_path UNINDEXED,
            start_line UNINDEXED,
            end_line UNINDEXED,
            tokenize = 'trigram'
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS index_meta_kv (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.commit()


def clear_all(conn: sqlite3.Connection) -> None:
    """清空索引（重建前调用）。"""
    cur = conn.cursor()
    cur.execute("DELETE FROM testcase_chunks")
    cur.execute("DELETE FROM index_meta_kv")
    conn.commit()


def insert_batch(
    conn: sqlite3.Connection,
    rows: list[dict[str, Any]],
) -> None:
    """批量插入记录。"""
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO testcase_chunks (
            uuid, title, section, body, file_path, start_line, end_line
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["uuid"],
                r["title"],
                r["section"],
                r["body"],
                r["file_path"],
                str(r["start_line"]),
                str(r["end_line"]),
            )
            for r in rows
        ],
    )


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO index_meta_kv (key, value) VALUES (?, ?)",
        (key, value),
    )


def commit(conn: sqlite3.Connection) -> None:
    conn.commit()


def prepare_chinese_search_terms(query: str) -> list[str]:
    """为中文构造检索词（单字、双字、英文词），与空格多关键词兼容。"""
    terms: list[str] = []
    query = query.strip()
    if not query:
        return terms
    keywords = [kw.strip() for kw in query.split() if kw.strip()]
    if not keywords:
        return terms
    for keyword in keywords:
        if keyword not in terms:
            terms.append(keyword)
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", keyword)
        for ch in chinese_chars:
            if ch not in terms:
                terms.append(ch)
        if len(chinese_chars) >= 2:
            for i in range(len(chinese_chars) - 1):
                bigram = chinese_chars[i] + chinese_chars[i + 1]
                if bigram not in terms:
                    terms.append(bigram)
        for word in re.findall(r"[a-zA-Z]+", keyword):
            if word.lower() not in [t.lower() for t in terms]:
                terms.append(word)
    return terms


def _fts_safe_term(t: str) -> str:
    """去掉会破坏 FTS 引号语法的字符。"""
    return t.replace('"', " ").strip()


def build_fts_match_query(query: str) -> str:
    """构造 FTS5 MATCH 子句。"""
    search_terms = prepare_chinese_search_terms(query)
    search_terms = [_fts_safe_term(x) for x in search_terms if _fts_safe_term(x)]
    if not search_terms:
        return ""
    keywords = [kw.strip() for kw in query.split() if kw.strip()]
    if len(keywords) > 1:
        keyword_queries = []
        for keyword in keywords:
            kterms = prepare_chinese_search_terms(keyword)
            kterms = [_fts_safe_term(x) for x in kterms if _fts_safe_term(x)]
            if not kterms:
                continue
            inner = " OR ".join([f'"{t}"' for t in kterms])
            keyword_queries.append(f"({inner})")
        return " AND ".join(keyword_queries) if keyword_queries else ""
    return " OR ".join([f'"{t}"' for t in search_terms])


def search_testcases(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 50,
    like_fallback_threshold: int = 3,
) -> list[dict[str, Any]]:
    """FTS MATCH 为主，命中过少时用 LIKE 补充。"""
    q = (query or "").strip()
    if not q:
        return []

    fts_q = build_fts_match_query(q)
    cur = conn.cursor()
    results: list[dict[str, Any]] = []

    fts_results: list[sqlite3.Row] = []
    if fts_q:
        try:
            cur.execute(
                """
                SELECT
                    uuid,
                    title,
                    section,
                    body,
                    file_path,
                    start_line,
                    end_line,
                    snippet(testcase_chunks, 1, '<mark>', '</mark>', '...', 24) AS title_snippet,
                    snippet(testcase_chunks, 2, '<mark>', '</mark>', '...', 48) AS section_snippet,
                    snippet(testcase_chunks, 3, '<mark>', '</mark>', '...', 96) AS body_snippet
                FROM testcase_chunks
                WHERE testcase_chunks MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_q, limit * 2),
            )
            fts_results = cur.fetchall()
        except sqlite3.OperationalError:
            fts_results = []

    seen: set[str] = set()
    search_terms = prepare_chinese_search_terms(q)

    def row_to_dict(row: sqlite3.Row, from_fts: bool) -> dict[str, Any]:
        uid = row["uuid"]
        title = row["title"] or ""
        section = row["section"] or ""
        body = row["body"] or ""
        d: dict[str, Any] = {
            "uuid": uid,
            "title": title,
            "section": section,
            "body": body,
            "file_path": row["file_path"],
            "start_line": int(row["start_line"] or 0),
            "end_line": int(row["end_line"] or 0),
        }
        if from_fts:
            d["title_snippet"] = row["title_snippet"]
            d["section_snippet"] = row["section_snippet"]
            d["body_snippet"] = row["body_snippet"]
        else:
            d["title_snippet"] = _manual_snippet(title, q)
            d["section_snippet"] = _manual_snippet(section, q)
            d["body_snippet"] = _manual_snippet(body, q)
        return d

    for row in fts_results:
        uid = row["uuid"]
        if uid not in seen:
            seen.add(uid)
            results.append(row_to_dict(row, True))
        if len(results) >= limit:
            return results

    if len(results) < like_fallback_threshold and search_terms:
        like_parts = []
        params: list[str] = []
        for term in search_terms:
            pat = f"%{term}%"
            like_parts.append(
                "(title LIKE ? OR section LIKE ? OR body LIKE ?)"
            )
            params.extend([pat, pat, pat])
        like_sql = " OR ".join(like_parts)
        cur.execute(
            f"""
            SELECT uuid, title, section, body, file_path, start_line, end_line,
                   title AS title_snippet, section AS section_snippet, body AS body_snippet
            FROM testcase_chunks
            WHERE {like_sql}
            LIMIT ?
            """,
            (*params, limit * 3),
        )
        for row in cur.fetchall():
            uid = row["uuid"]
            if uid not in seen:
                seen.add(uid)
                results.append(row_to_dict(row, False))
            if len(results) >= limit:
                break

    return results[:limit]


def _manual_snippet(text: str, query: str, max_len: int = 120) -> str:
    if not text:
        return ""
    low = text.lower()
    qlow = query.lower().strip()
    if qlow and qlow in low:
        pos = low.find(qlow)
        start = max(0, pos - 24)
        end = min(len(text), pos + len(query) + 80)
        frag = text[start:end]
        if start > 0:
            frag = "..." + frag
        if end < len(text):
            frag = frag + "..."
        return frag.replace(query, f"<mark>{query}</mark>") if query else frag
    return text[:max_len] + ("..." if len(text) > max_len else "")


def write_index_meta_json(
    output_path: Path,
    payload: dict[str, Any],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "connect",
    "init_schema",
    "clear_all",
    "insert_batch",
    "set_meta",
    "commit",
    "search_testcases",
    "write_index_meta_json",
    "utc_now_iso",
]
