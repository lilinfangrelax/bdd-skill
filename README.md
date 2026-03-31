# bdd-skill

借助 BDD 实现软件测试效率提升。

## 安装依赖

在项目根目录使用虚拟环境（`.venv`）后执行：

```bash
pip install -e .
```

## Skills 总览

本项目当前包含 5 个核心 Skill，覆盖从录制 trace 到落地 `bdd_project` 的完整链路。

### 1) playwright-trace-recorder

- **用途**：将已有 Playwright Python 录制脚本改造成可稳定产出 `trace.zip` 的执行脚本，并降低末尾响应丢失概率。
- **触发语**：
  - `录制 trace.zip`
  - `Playwright trace`
  - `脚本改造后抓 trace`
  - `trace 最后几条响应没抓到`
- **输入**：已有录制脚本（如 `recording.py` / `task.py`）。
- **输出**：`trace.zip`。
- **用法**：
  - 在脚本中增加 `context.tracing.start(...)` 与 `context.tracing.stop(path="trace.zip")`
  - 在 `stop` 前执行：关键响应等待 + `networkidle` + 短暂 `wait_for_timeout(...)`
  - 在项目根目录运行：`.\.venv\Scripts\python demo/trace_click_api/recordings/task.py`

### 2) trace-to-bdd

- **用途**：将录制脚本中的 `# 注释 step` 与 `trace_parsed.json` 合并，生成可勾选的 BDD 确认 Markdown。
- **触发语**：
  - `生成 BDD 步骤`
  - `trace 转 markdown`
  - `将录制脚本和 trace JSON 生成 BDD 确认文件`
- **输入**：
  - `recording.py`（含 `# 注释`）
  - `trace_parsed.json`
- **输出**：`bdd_confirmed.md`（GFM checkbox 形式）。
- **用法**：
  - `python scripts/trace_to_bdd.py <recording.py> <trace_parsed.json> <output.md>`

### 3) md-to-api-steps

- **用途**：读取用户勾选后的 `bdd_confirmed.md` 和原始 `trace.zip`，提取真实 request/response，并推断 `ctx` 依赖，生成 API 自动化步骤 Markdown。
- **触发语**：
  - `根据选好的接口生成自动化步骤`
  - `md 转 api steps`
  - `生成接口自动化测试用例`
- **输入**：
  - `bdd_confirmed.md`
  - `trace.zip`
- **输出**：`api_steps.md`（包含 Request/Response 与 `ctx` 依赖标注）。
- **用法**：
  - `python scripts/md_to_api_steps.py <bdd_confirmed.md> <trace.zip> <output.md>`

### 4) api-steps-to-bdd-project

- **用途**：将 `api_steps.md` 解析为 pytest-bdd 可用 fixture，并在目标 `bdd_project` 追加 API Scenario 与 steps 脚手架。
- **触发语**：
  - `api_steps 接入 bdd_project`
  - `api_steps 转 feature/fixture`
  - `生成 API BDD 脚手架`
- **输入**：
  - `api_steps.md`
  - `bdd_project` 根路径
  - 可选：feature 路径、Scenario 名、fixture 输出路径
- **输出**：
  - `fixtures/api_steps/*.json`
  - 更新后的 `.feature`
  - `steps/api/generated_api_steps.py`
- **用法**：
  - `python scripts/api_steps_to_bdd_project.py <api_steps.md> <bdd_project_root> [选项]`

### 5) markdown-testcase-fts-search

- **用途**：对单个超大 Markdown 构建 SQLite FTS5 检索索引，并支持关键词查询（`MATCH` + `LIKE` 回退）。
- **触发语**：
  - `整份 md 检索`
  - `Markdown 全文搜索`
  - `测试用例 FTS`
  - `大文件检索`
- **输入**：单个 `.md` 文件路径（可选输出目录和批处理参数）。
- **输出**：
  - `testcases_fts.db`
  - `index_meta.json`
- **用法**：
  - 建索引：`python .claude/skills/markdown-testcase-fts-search/scripts/build_index.py --input <all_cases.md> --output-dir <out_dir>`
  - 检索：`python .claude/skills/markdown-testcase-fts-search/scripts/query_index.py --db <testcases_fts.db> --query "关键字1 关键字2" --top-k 20 --format markdown`

## 推荐使用流程（端到端）

1. 用 `playwright-trace-recorder` 产出稳定的 `trace.zip`
2. 解析 trace 后，使用 `trace-to-bdd` 生成勾选式 BDD 确认文档
3. 用户勾选后，使用 `md-to-api-steps` 生成 `api_steps.md`
4. 使用 `api-steps-to-bdd-project` 接入目标 `bdd_project`
5. 如需在超大测试文档中检索，再使用 `markdown-testcase-fts-search`
