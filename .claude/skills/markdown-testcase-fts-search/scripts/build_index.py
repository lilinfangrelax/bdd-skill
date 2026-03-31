# -*- coding: utf-8 -*-
"""
从单份 Markdown 构建 SQLite FTS5 索引（流式、分批提交，适配超大文件）。

用法:
  python build_index.py --input path/to/cases.md --output-dir ./fts_out
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

# 保证可脚本直接运行
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from adaptive_parser import ParserConfig, iter_markdown_records  # noqa: E402
from fts_store import (  # noqa: E402
    clear_all,
    commit,
    connect,
    init_schema,
    insert_batch,
    set_meta,
    utc_now_iso,
    write_index_meta_json,
)


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="为单份 Markdown 构建 FTS5 索引")
    parser.add_argument("--input", "-i", required=True, type=Path, help="输入的 Markdown 文件路径")
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="输出目录（默认：与输入文件同目录下的 .markdown_fts_index）",
    )
    parser.add_argument("--batch-size", type=int, default=80, help="每批插入行数")
    parser.add_argument(
        "--commit-interval",
        type=int,
        default=400,
        help="每累计多少条记录提交一次事务（大文件建议 200～1000）",
    )
    parser.add_argument("--max-section-chars", type=int, default=32000)
    parser.add_argument("--chunk-lines", type=int, default=120)
    parser.add_argument(
        "--split-on-hr",
        action="store_true",
        help="在单独一行的 --- 处尝试切段（可能误切，按需开启）",
    )
    parser.add_argument(
        "--no-split-blank-lines",
        action="store_true",
        help="关闭「连续空行切段」（默认开启：连续空行达到阈值视为一条完整用例结束）",
    )
    parser.add_argument(
        "--min-blank-lines",
        type=int,
        default=2,
        help="连续多少行空行触发切段（默认 2）",
    )
    parser.add_argument(
        "--progress-lines",
        type=int,
        default=20000,
        help="每读多少行向 stderr 打印进度，0 表示关闭",
    )
    parser.add_argument("--force", action="store_true", help="删除已有索引文件再重建")
    args = parser.parse_args()

    md_path: Path = args.input
    if not md_path.is_file():
        print(f"错误：找不到文件 {md_path}", file=sys.stderr)
        return 1

    out_dir = args.output_dir
    if out_dir is None:
        out_dir = md_path.parent / ".markdown_fts_index"
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    db_path = out_dir / "testcases_fts.db"
    meta_path = out_dir / "index_meta.json"

    if args.force and db_path.exists():
        db_path.unlink()

    cfg = ParserConfig(
        chunk_lines=args.chunk_lines,
        max_section_chars=args.max_section_chars,
        split_on_horizontal_rule=args.split_on_hr,
        split_on_consecutive_blank_lines=not args.no_split_blank_lines,
        min_consecutive_blank_lines=max(2, args.min_blank_lines),
    )

    conn = connect(db_path)
    init_schema(conn)
    clear_all(conn)

    source_hash = _sha256_file(md_path)
    set_meta(conn, "source_path", str(md_path.resolve()))
    set_meta(conn, "source_sha256", source_hash)
    set_meta(conn, "built_at", utc_now_iso())
    commit(conn)

    progress_every = args.progress_lines if args.progress_lines > 0 else 0

    batch: list[dict] = []
    total = 0
    since_commit = 0

    try:
        for rec in iter_markdown_records(
            md_path,
            config=cfg,
            progress_every_lines=progress_every,
        ):
            batch.append(rec)
            if len(batch) >= args.batch_size:
                insert_batch(conn, batch)
                n = len(batch)
                total += n
                since_commit += n
                batch.clear()
                if since_commit >= args.commit_interval:
                    commit(conn)
                    since_commit = 0
                    print(f"[build] 已索引约 {total} 条记录 …", file=sys.stderr)

        if batch:
            insert_batch(conn, batch)
            total += len(batch)
            batch.clear()
        commit(conn)
    except Exception as e:
        print(f"构建失败: {e}", file=sys.stderr)
        raise

    payload = {
        "source_file": str(md_path.resolve()),
        "source_sha256": source_hash,
        "built_at": utc_now_iso(),
        "record_count": total,
        "output_db": str(db_path),
        "options": {
            "batch_size": args.batch_size,
            "commit_interval": args.commit_interval,
            "max_section_chars": args.max_section_chars,
            "chunk_lines": cfg.chunk_lines,
            "split_on_horizontal_rule": cfg.split_on_horizontal_rule,
            "split_on_consecutive_blank_lines": cfg.split_on_consecutive_blank_lines,
            "min_consecutive_blank_lines": cfg.min_consecutive_blank_lines,
        },
    }
    write_index_meta_json(meta_path, payload)
    print(f"完成：共 {total} 条记录，数据库 {db_path}", file=sys.stderr)
    print(str(db_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
