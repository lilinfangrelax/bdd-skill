# -*- coding: utf-8 -*-
"""
单份 Markdown 自适应切分（启发式，不依赖固定「测试用例字段」标题）。

大文件：仅按行流式读取，不在内存中保留整文件；仅在当前用例块内累积文本。
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

# 二级标题（排除 ###）
_RE_H2 = re.compile(r"^## (?!#)\s*(.+?)\s*$")
# 三级标题
_RE_H3 = re.compile(r"^### (?!#)\s*(.+?)\s*$")
# 水平分隔线（独立一行）
_RE_HR = re.compile(r"^---+\s*$")
# 围栏代码块
_RE_FENCE = re.compile(r"^(\s*)(```|~~~)")


SplitMode = Literal["h2", "h3", "chunk"]


@dataclass
class ParserConfig:
    """解析与切分参数（大文件场景可调）。"""

    # 探测前 N 行以决定按 H2 / H3 / 纯分块
    probe_max_lines: int = 800
    # 无标题结构时，每多少行合成一个可检索块
    chunk_lines: int = 120
    # 单条 body 超过此长度则拆成多条（避免 FTS 行过大）
    max_section_chars: int = 32000
    # 是否在 HR --- 处强制切段（若上一段已有内容）
    split_on_horizontal_rule: bool = False


def _detect_split_mode(lines_probe: list[str]) -> SplitMode:
    """根据文档前若干行判断主要分段方式。"""
    h2 = 0
    h3 = 0
    in_fence = False
    fence_mark = ""
    for line in lines_probe:
        m = _RE_FENCE.match(line)
        if m:
            mark = m.group(2)
            if not in_fence:
                in_fence = True
                fence_mark = mark
            elif mark == fence_mark:
                in_fence = False
            continue
        if in_fence:
            continue
        if _RE_H2.match(line):
            h2 += 1
        elif _RE_H3.match(line):
            h3 += 1
    if h2 >= 2:
        return "h2"
    if h3 >= 2:
        return "h3"
    return "chunk"


def _split_long_body(
    body: str,
    *,
    title: str,
    section: str,
    file_path: str,
    start_line: int,
    end_line: int,
    max_chars: int,
) -> Iterator[dict]:
    """将过长正文拆成多条记录，便于 FTS 与内存友好。"""
    if len(body) <= max_chars:
        uid = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{file_path}:{start_line}:{section}:0",
            )
        )
        yield {
            "uuid": uid,
            "title": title,
            "section": section,
            "body": body,
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
        }
        return
    total_parts = (len(body) + max_chars - 1) // max_chars
    for i, pos in enumerate(range(0, len(body), max_chars)):
        chunk = body[pos : pos + max_chars]
        sec = f"{section} [片段 {i + 1}/{total_parts}]"
        uid = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{file_path}:{start_line}:{section}:{i}",
            )
        )
        yield {
            "uuid": uid,
            "title": title,
            "section": sec,
            "body": chunk,
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
        }


def iter_markdown_records(
    md_path: Path,
    *,
    config: ParserConfig | None = None,
    progress_every_lines: int = 0,
) -> Iterator[dict]:
    """
    流式遍历 Markdown，产出可供 FTS 入库的记录。

    :param md_path: 源文件路径
    :param config: 解析配置
    :param progress_every_lines: 若 >0，每处理这么多行向 stderr 打印进度
    """
    cfg = config or ParserConfig()
    path_str = str(md_path.resolve())

    # 第一遍：只读前 probe_max_lines 用于探测结构（大文件友好）
    probe: list[str] = []
    with md_path.open("r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            probe.append(line)
            if i + 1 >= cfg.probe_max_lines:
                break

    split_mode = _detect_split_mode(probe)

    # 第二遍：全文件流式处理
    buffer: list[str] = []
    buf_start_line = 1
    current_title = ""
    in_fence = False
    fence_mark = ""

    line_no = 0
    chunk_idx = 0  # chunk 模式下片段序号

    def flush_buffer_as_records(
        title: str,
        section_default: str,
        start_ln: int,
        end_ln: int,
    ) -> Iterator[dict]:
        nonlocal buffer
        if not buffer:
            return
        body = "".join(buffer).strip()
        buffer = []
        if not body:
            return
        yield from _split_long_body(
            body,
            title=title or "(未命名块)",
            section=section_default,
            file_path=path_str,
            start_line=start_ln,
            end_line=end_ln,
            max_chars=cfg.max_section_chars,
        )

    with md_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_no += 1
            if progress_every_lines and line_no % progress_every_lines == 0:
                import sys

                print(f"[parse] 已读行数: {line_no}", file=sys.stderr)

            fm = _RE_FENCE.match(line)
            if fm:
                mark = fm.group(2)
                if not in_fence:
                    in_fence = True
                    fence_mark = mark
                elif mark == fence_mark:
                    in_fence = False
                buffer.append(line)
                continue

            if in_fence:
                buffer.append(line)
                continue

            # 水平线：可选切段
            if cfg.split_on_horizontal_rule and _RE_HR.match(line.strip()):
                if buffer:
                    end_ln = line_no - 1
                    title = current_title or f"片段-{chunk_idx}"
                    yield from flush_buffer_as_records(
                        title,
                        "horizontal_rule",
                        buf_start_line,
                        end_ln,
                    )
                    buf_start_line = line_no + 1
                buffer.append(line)
                continue

            heading_h2 = _RE_H2.match(line) if split_mode == "h2" else None
            heading_h3 = _RE_H3.match(line) if split_mode == "h3" else None

            if split_mode == "h2" and heading_h2:
                if buffer:
                    end_ln = line_no - 1
                    yield from flush_buffer_as_records(
                        current_title or "(文档开头)",
                        "body",
                        buf_start_line,
                        end_ln,
                    )
                current_title = heading_h2.group(1).strip()
                buf_start_line = line_no
                buffer = [line]
                continue

            if split_mode == "h3" and heading_h3:
                if buffer:
                    end_ln = line_no - 1
                    yield from flush_buffer_as_records(
                        current_title or "(文档开头)",
                        "body",
                        buf_start_line,
                        end_ln,
                    )
                current_title = heading_h3.group(1).strip()
                buf_start_line = line_no
                buffer = [line]
                continue

            if split_mode == "chunk":
                buffer.append(line)
                if len(buffer) >= cfg.chunk_lines:
                    chunk_idx += 1
                    end_ln = line_no
                    body_lines = buffer
                    body = "".join(body_lines).strip()
                    if body:
                        title = f"文档片段-{chunk_idx}"
                        yield from _split_long_body(
                            body,
                            title=title,
                            section="chunk",
                            file_path=path_str,
                            start_line=buf_start_line,
                            end_line=end_ln,
                            max_chars=cfg.max_section_chars,
                        )
                    buffer = []
                    buf_start_line = line_no + 1
                continue

            buffer.append(line)

        # 文件结束：刷尾
        if buffer:
            end_ln = line_no
            if split_mode == "chunk":
                chunk_idx += 1
                body = "".join(buffer).strip()
                if body:
                    title = f"文档片段-{chunk_idx}"
                    yield from _split_long_body(
                        body,
                        title=title,
                        section="chunk",
                        file_path=path_str,
                        start_line=buf_start_line,
                        end_line=end_ln,
                        max_chars=cfg.max_section_chars,
                    )
            else:
                yield from flush_buffer_as_records(
                    current_title or "(文档末尾)",
                    "body",
                    buf_start_line,
                    end_ln,
                )


__all__ = ["ParserConfig", "iter_markdown_records", "SplitMode"]
