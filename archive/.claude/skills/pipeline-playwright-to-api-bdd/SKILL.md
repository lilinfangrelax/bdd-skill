---
name: pipeline-playwright-to-api-bdd
description: >
  总控向导：将 Playwright 录制脚本执行 → trace 解析 → BDD 确认勾选 → API 步骤生成 → bdd_project 接入
  的完整流程收敛为单入口分步向导。录制脚本未通过硬闸门时阻断，人工勾选强制经过，任意阶段失败可定位/可续跑。
  当用户提到「一键生成 BDD」「从录制到 bdd_project」「跑完整流程」「向导式生成」「单入口向导」时使用。
  输入：录制脚本路径（或已有 trace.zip）、bdd_project 根路径。
  输出：runs/<timestamp>/ 下全部中间产物 + bdd_project 中的 fixture / feature / generated steps。
---

# Pipeline: Playwright 录制 → API BDD（总控向导）

## 概述

本 skill 是一个**分步向导式总控**，串联以下已有能力（不重写底层脚本）：

1. 录制脚本执行与 trace 验证（硬闸门）
2. trace.zip 解析为结构化 JSON
3. 录制脚本注释 + trace JSON → BDD 确认 Markdown
4. **人工勾选（必经暂停点）**
5. 勾选 MD + trace.zip → API 步骤 Markdown
6. API 步骤 → bdd_project fixture / feature / generated steps

所有阶段产物统一存放在 `runs/<timestamp>/` 目录，通过 `pipeline_state.json` 记录进度，
支持失败后从任意阶段续跑。

## 前置条件

- 已有可执行的 Playwright 录制脚本（含 `# 注释` 作为 BDD step 标签）
- 录制脚本的目标应用已启动（如需本地 server 则先手动启动）
- Python 虚拟环境 `.venv` 可用

---

## 执行方式

### 首次启动

```powershell
.\.venv\Scripts\python ".claude/skills/pipeline-playwright-to-api-bdd/scripts/pipeline_orchestrator.py" start `
  --recording-script "demo/trace_click_api/recordings/task.py" `
  --bdd-project "bdd_project"
```

可选参数：

| 参数 | 说明 |
|------|------|
| `--trace-zip <path>` | 直接使用已有 trace.zip（跳过录制验证阶段） |
| `--trace-output <path>` | 录制脚本产出 trace.zip 的路径（自动检测时可省略） |
| `--scenario-name <name>` | 自定义 Scenario 名（默认「用户完整操作任务（API）」） |
| `--runs-root <dir>` | 自定义 runs 根目录（默认 `runs`） |

### 继续执行（人工勾选后）

```powershell
.\.venv\Scripts\python ".claude/skills/pipeline-playwright-to-api-bdd/scripts/pipeline_orchestrator.py" continue `
  --run-dir "runs/<timestamp>"
```

### 从指定阶段重试

```powershell
.\.venv\Scripts\python ".claude/skills/pipeline-playwright-to-api-bdd/scripts/pipeline_orchestrator.py" resume-from <stage> `
  --run-dir "runs/<timestamp>"
```

### 查看状态

```powershell
.\.venv\Scripts\python ".claude/skills/pipeline-playwright-to-api-bdd/scripts/pipeline_orchestrator.py" status `
  --run-dir "runs/<timestamp>"
```

---

## 向导阶段定义

| # | 阶段 | 说明 | 闸门 |
|---|------|------|------|
| 1 | `validate_recording_script` | 执行录制脚本，验证 trace.zip 有效 | 硬闸门：退出码 0 + trace.zip 存在 + 含有效请求响应 |
| 2 | `record_or_use_trace` | 复用验证阶段 trace 或使用用户提供的 trace.zip | — |
| 3 | `trace_to_bdd_confirm` | 解析 trace → JSON → 生成 bdd_confirmed.md 初稿 | — |
| 4 | `human_confirm_required` | **暂停**，等待用户编辑 bdd_confirmed.md | 至少一个 `[x]` 勾选 |
| 5 | `confirmed_md_to_api_steps` | 勾选 MD + trace.zip → api_steps.md | — |
| 6 | `api_steps_to_bdd_project` | api_steps.md → fixture / feature / generated steps | — |
| 7 | `done` | 输出最终产物路径与后续接入提示 | — |

---

## 产物目录

```
runs/<timestamp>/
├── pipeline_state.json     # 阶段状态、参数、错误信息
├── trace.zip               # trace（从录制输出复制）
├── trace_parsed.json       # parse_trace.py 输出
├── bdd_confirmed.md        # 人工勾选用
└── api_steps.md            # 最终 API 步骤
```

bdd_project 内生成的文件（默认路径）：
- `bdd_project/fixtures/api_steps/task_api.json`
- `bdd_project/features/task.feature`（追加 Scenario）
- `bdd_project/steps/api/generated_api_steps.py`

---

## Agent 操作步骤

1. 读取本 SKILL.md
2. 确认用户提供的录制脚本路径与 bdd_project 路径
3. 如需要，先启动目标应用（如 `demo/trace_click_api/server.py`）
4. 执行 `start` 命令
5. 脚本自动执行到 `human_confirm_required` 暂停
6. **告知用户** `bdd_confirmed.md` 的完整路径，请其编辑勾选
7. 用户确认编辑完成后，执行 `continue` 命令
8. 脚本跑完剩余阶段直到 `done`
9. 输出最终产物路径，提示用户在 `test_api.py` 中接入 `generated_api_steps` 模块

---

## 前提闸门细则（录制脚本必须成功）

仅当以下条件**同时满足**时，`validate_recording_script` 标记为通过：

- 录制脚本进程退出码为 0
- 在脚本附近目录或指定路径找到 `trace.zip`
- trace.zip 中包含 `trace.trace` 与 `trace.network` 成员
- trace.network 中存在状态码大于 0 的请求响应（非 pending）

闸门失败时：
- `pipeline_state.json` 写入失败原因与建议修复动作
- 流水线直接停止，不进入后续阶段
- 可通过 `resume-from validate_recording_script` 重试

---

## 失败恢复

- 每个阶段完成后立即更新 `pipeline_state.json`
- `resume-from <stage>` 回退到指定阶段并重新执行（不重复已跳过的阶段）
- 常见错误均附带明确提示信息

---

## 常见错误与排查

| 错误 | 阶段 | 排查 |
|------|------|------|
| 录制脚本退出码非 0 | validate_recording_script | 目标应用是否启动？脚本路径是否正确？ |
| 未找到 trace.zip | validate_recording_script | 检查 `tracing.stop(path=...)` 路径，或用 `--trace-output` 指定 |
| trace 中请求全是 pending | validate_recording_script | 参考 `playwright-trace-recorder` skill 加等待策略 |
| bdd_confirmed.md 无 [x] | human_confirm_required | 至少勾选一个接口再 continue |
| trace.zip 中无匹配 body | confirmed_md_to_api_steps | body 留空（`// TODO`），可后续手动补充 |
| api_steps.md 无法解析 | api_steps_to_bdd_project | 检查 MD 格式是否符合 `## 标题` + `**METHOD** \`url\`` 规范 |
