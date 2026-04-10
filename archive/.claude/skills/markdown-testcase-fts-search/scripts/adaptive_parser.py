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
# 四级标题（部分平台用 #### 作为单条用例标题）
_RE_H4 = re.compile(r"^#### (?!#)\s*(.+?)\s*$")
# 水平分隔线（独立一行）
_RE_HR = re.compile(r"^---+\s*$")
# 围栏代码块
_RE_FENCE = re.compile(r"^(\s*)(```|~~~)")


SplitMode = Literal["h2", "h3", "h4", "chunk"]


@dataclass
class ParserConfig:
    """解析与切分参数（大文件场景可调）。"""

    # 无标题结构时，每多少行合成一个可检索块
    chunk_lines: int = 120
    # 单条 body 超过此长度则拆成多条（避免 FTS 行过大）
    max_section_chars: int = 32000
    # 是否在 HR --- 处强制切段（若上一段已有内容）
    split_on_horizontal_rule: bool = False
    # 连续多行空行是否视为「一条完整用例/段落」结束（平台纯文本导出常用）
    split_on_consecutive_blank_lines: bool = True
    # 连续空行达到多少行时切段（默认 2：即两个 \\n\\n 之间的块）
    min_consecutive_blank_lines: int = 2


def _first_line_as_title(body: str, max_len: int = 100) -> str:
    """取正文首行非空内容作为展示标题。"""
    for ln in body.splitlines():
        s = ln.strip()
        if s:
            return s[:max_len]
    return "(空块)"


def _fence_aware_count_headings(
    lines: Iterator[str],
) -> tuple[int, int, int]:
    """统计 ## / ### / #### 出现次数（忽略代码围栏内）。"""
    h2 = h3 = h4 = 0
    in_fence = False
    fence_mark = ""
    for line in lines:
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
        elif _RE_H4.match(line):
            h4 += 1
    return h2, h3, h4


def _detect_split_mode_from_counts(h2: int, h3: int, h4: int) -> SplitMode:
    """
    根据全文件标题数量决定分段层级。

    典型导出问题：文首即有多个「## 模块」，旧逻辑会误判为按 H2 切分，
    而真实用例在「### 用例名」下，导致数千条用例被合并成少量大块再被 max_section_chars 切碎。
    因此：当 ### / #### 数量明显多于上一级时，优先按更深标题切分。
    """
    # 四级标题占多数（每条用例一个 ####）
    if h4 >= 2 and h4 >= max(h2, h3) * 2:
        return "h4"
    # 三级标题远多于二级：少量模块(##) + 大量用例(###)
    if h3 >= 2:
        if h2 == 0 or h3 >= h2 * 2 or (h2 <= 5 and h3 >= h2 + 20):
            return "h3"
    if h2 >= 2:
        return "h2"
    if h3 >= 2:
        return "h3"
    if h4 >= 2:
        return "h4"
    return "chunk"


def _stream_count_headings_file(md_path: Path) -> tuple[int, int, int]:
    """整文件流式统计标题（大文件仅多一次顺序读，不占内存）。"""
    with md_path.open("r", encoding="utf-8", errors="replace") as f:
        return _fence_aware_count_headings(f)


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

    # 整文件流式统计标题（一次顺序读，仅计数，用于避免「文首误判 H2」）
    h2_n, h3_n, h4_n = _stream_count_headings_file(md_path)
    split_mode = _detect_split_mode_from_counts(h2_n, h3_n, h4_n)

    # 第二遍：全文件流式处理
    buffer: list[str] = []
    buf_start_line = 1
    current_title = ""
    in_fence = False
    fence_mark = ""

    line_no = 0
    chunk_idx = 0  # chunk 模式下片段序号
    consecutive_empty = 0  # 连续空行计数（围栏外）

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
                if not buffer:
                    buf_start_line = line_no
                buffer.append(line)
                continue

            # 连续空行：可视为一条完整用例/文本块结束（与标题分段叠加）
            if cfg.split_on_consecutive_blank_lines:
                is_empty = not line.strip()
                if is_empty:
                    consecutive_empty += 1
                    if (
                        buffer
                        and consecutive_empty >= cfg.min_consecutive_blank_lines
                    ):
                        end_ln = line_no - cfg.min_consecutive_blank_lines
                        body_text = "".join(buffer).strip()
                        buffer = []
                        consecutive_empty = 0
                        if body_text:
                            if split_mode == "chunk":
                                chunk_idx += 1
                                blk_title = f"文档片段-{chunk_idx}"
                                sec = "blank_paragraph"
                            else:
                                blk_title = _first_line_as_title(body_text)
                                sec = "blank_paragraph"
                            yield from _split_long_body(
                                body_text,
                                title=blk_title,
                                section=sec,
                                file_path=path_str,
                                start_line=buf_start_line,
                                end_line=end_ln,
                                max_chars=cfg.max_section_chars,
                            )
                        continue
                    if buffer:
                        buffer.append(line)
                        continue
                    continue
                consecutive_empty = 0

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
            heading_h4 = _RE_H4.match(line) if split_mode == "h4" else None

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

            if split_mode == "h4" and heading_h4:
                if buffer:
                    end_ln = line_no - 1
                    yield from flush_buffer_as_records(
                        current_title or "(文档开头)",
                        "body",
                        buf_start_line,
                        end_ln,
                    )
                current_title = heading_h4.group(1).strip()
                buf_start_line = line_no
                buffer = [line]
                continue

            if split_mode == "chunk":
                if not buffer:
                    buf_start_line = line_no
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

            if not buffer:
                buf_start_line = line_no
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
            elif split_mode in ("h2", "h3", "h4"):
                yield from flush_buffer_as_records(
                    current_title or "(文档末尾)",
                    "body",
                    buf_start_line,
                    end_ln,
                )


__all__ = ["ParserConfig", "iter_markdown_records", "SplitMode"]
