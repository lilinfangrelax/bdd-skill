---
name: markdown-testcase-fts-search
description: >
  将单份超大 Markdown（含全部测试用例或说明文本）解析为可检索片段，构建 SQLite FTS5 索引并支持关键词检索（MATCH + LIKE 回退）。
  不依赖固定「用例字段」标题；默认启发式分段，亦可由 Agent 先整理结构再入库。
  当用户提到「整份 md 检索」「Markdown 全文搜索」「测试用例 FTS」「大文件检索」时使用。
  输入：① 单个 .md 文件路径 ② 可选输出目录与批处理参数。
  输出：testcases_fts.db、index_meta.json；检索结果支持 JSON / Markdown。
---

# Markdown 测试用例 FTS5 检索 Skill

## 适用场景

- 用例集中在一个 **体积很大** 的 Markdown 文件中，不便拆成多文件。
- 需要 **关键词检索**（非语义向量），离线、可复现、依赖少（仅需 Python 标准库 + SQLite FTS5）。
- **不强制** 「测试用例名称 / 前置条件」等固定章节名；解析器用标题层级与分块行数自适应；若文档结构特殊，可由 **Agent 先阅读并预处理** 成易分段格式再建索引。

## 输出产物

| 文件 | 说明 |
|------|------|
| `testcases_fts.db` | SQLite 数据库，内含 FTS5 虚拟表 `testcase_chunks`（`tokenize='trigram'`，利于中文） |
| `index_meta.json` | 源文件路径、SHA256、记录条数、构建参数等 |

默认输出目录：与输入文件同目录下的 **`.markdown_fts_index/`**（可用 `--output-dir` 覆盖）。

## 超大 Markdown 的兼容策略

1. **流式读取**：解析器按行扫描，不在内存中保存整文件。
2. **分段策略（自动探测）**：读取前若干行统计 `##` / `###` 数量，优先按 **二级标题** 分段；否则按 **三级标题**；若几乎没有标题，则按 **固定行数** 切成「文档片段-N」。
3. **超长片段**：单段正文超过 `--max-section-chars` 时拆成多条索引记录（`section` 中带 `[片段 i/n]`）。
4. **批量插入与分批提交**：`--batch-size` 控制 `executemany` 批量大小；`--commit-interval` 控制每隔多少条 `commit` 一次，降低大事务内存与 WAL 压力。
5. **进度日志**：`--progress-lines` 设为大于 0 时，每隔 N 行向 stderr 打印解析进度。

## 脚本说明

脚本目录：`.claude/skills/markdown-testcase-fts-search/scripts/`（将 `scripts` 加入 `PYTHONPATH` 后也可作为模块使用）。

### 1. 建索引：`build_index.py`

```bash
cd .claude/skills/markdown-testcase-fts-search/scripts
python build_index.py --input /path/to/all_cases.md --output-dir /path/to/out
```

常用参数：

| 参数 | 说明 |
|------|------|
| `--input` | 必填，源 Markdown 路径 |
| `--output-dir` | 输出目录，默认 `输入文件目录/.markdown_fts_index` |
| `--batch-size` | 每批插入条数，默认 80 |
| `--commit-interval` | 每隔多少条提交事务，默认 400 |
| `--max-section-chars` | 单条 body 最大字符数，默认 32000 |
| `--chunk-lines` | 无标题时的分块行数，默认 120 |
| `--probe-max-lines` | 用于探测结构的预览行数，默认 800 |
| `--split-on-hr` | 是否在单独的 `---` 行处切段（可能误切，慎用） |
| `--progress-lines` | 每读多少行打印进度，默认 20000；0 关闭 |
| `--force` | 删除已有 `testcases_fts.db` 后重建 |

成功时 stdout 打印数据库路径，stderr 打印摘要。

### 2. 检索：`query_index.py`

```bash
python query_index.py --db /path/to/out/testcases_fts.db --query "关键字1 关键字2" --top-k 20 --format json
```

| 参数 | 说明 |
|------|------|
| `--db` | `testcases_fts.db` 路径 |
| `--query` | 关键词；空格分隔多个词时，内部按 AND 组合（与 teshi 侧思路一致） |
| `--top-k` | 最多返回条数 |
| `--format` | `markdown`（默认）或 `json` |

## Agent 协作建议

1. **结构极不规则** 时：Agent 可先通读目录与标题，给出「按 H2 切」或「按自定义正则切」的建议；必要时可 **生成中间 Markdown**（例如只保留 `## 用例标题` + 正文）再调用 `build_index.py`。
2. **仅检索部分目录**：先用 Agent 或脚本抽取子文档，再对子文档建索引。
3. **重建索引**：源文件更新后应带 `--force` 重建，或删除输出目录再运行；`index_meta.json` 中 `source_sha256` 可用于判断是否需要重建。

## 依赖

- Python 3.10+
- **无需** 额外 pip 包；使用标准库 `sqlite3`（需 SQLite 支持 FTS5 与 trigram；一般 Python 自带版本已满足）。

## 与 teshi 的关系

- **思想对齐**：FTS5 + `trigram`、中文多词扩展、MATCH 与 LIKE 回退。
- **不对接** teshi 或 PySide6；本 skill 仅提供 **可脚本化** 的建库与查询，便于在任意环境或 Agent 流水线中调用。
