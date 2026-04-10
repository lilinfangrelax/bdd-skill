---
name: trace-zip-to-json
description: >
  将 Playwright 生成的 trace.zip 解析为结构化 JSON（UI 操作 + 网络请求 + 时间窗口关联 + orphan 请求）。
  当用户提到“解析 trace.zip 到 json”“trace zip 转 json”“提取 UI 与 API 对应关系”时使用。
  输入：① trace.zip 路径 ② 可选 lookahead、是否包含 document 请求。
  输出：trace_parsed.json（可选同时输出 markdown 摘要）。
---

# Trace ZIP -> JSON Skill

## 目标

把 Playwright 的 `trace.zip` 解析为可机读 JSON，核心结果包含：

- `actions`：UI 操作序列（如 `Frame.click`、`Frame.fill`）
- `matched_requests`：每个 UI 操作关联到的接口请求
- `orphan_requests`：未匹配到任何 UI 操作窗口的请求
- `diagnostics`：解析过程诊断信息

---

## 依赖与前置

- 解析脚本：`demo/trace_click_api/parse_trace.py`
- Python 环境：必须使用项目根目录 `.venv`

Windows PowerShell 示例：

```powershell
.\.venv\Scripts\python "demo/trace_click_api/parse_trace.py" --zip "<trace.zip路径>" --json-out "<输出json路径>"
```

---

## 输入参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--zip` | 是 | Playwright 生成的 `trace.zip` |
| `--json-out` | 否 | JSON 输出路径；不传则打印到 stdout |
| `--markdown-out` | 否 | Markdown 摘要输出路径 |
| `--lookahead` | 否 | 操作结束后的前瞻窗口毫秒数，默认 `1500` |
| `--no-next-cap` | 否 | 不用下一操作开始时间截断窗口上界 |
| `--include-document` | 否 | 包含主文档 `text/html` 的 GET 请求 |

---

## 核心实现（脚本内部机制）

### 1) 解压并定位成员

- 打开 zip 后定位 `trace.trace` 与 `trace.network`
- 支持路径前缀差异（不是硬编码根目录）
- 缺任一成员直接报错

### 2) 解析 `trace.trace`（UI 操作）

- 读取 NDJSON（逐行 JSON）
- 用 `before/after + callId` 合并出完整调用
- 仅保留 `Frame` 的用户方法（`click`、`fill`、`goto` 等）
- 产出 `ActionStep`：`api_name`、`params`、`start_time`、`end_time`

### 3) 解析 `trace.network`（网络请求）

- 优先解析 `resource-snapshot`（HAR 在 `snapshot` 内）
- 兼容 `resource` 旧结构
- 过滤静态资源（`.js/.css/.png/.woff...`）
- 默认过滤主文档 GET（可通过 `--include-document` 打开）

### 4) 时间窗口关联

对每个 action 计算窗口：

- 下界：`action.start_time`
- 上界：`min(action.end_time + lookahead_ms, next_action.start_time)`（默认）

每个请求归入“第一个覆盖其时间点”的 action；未命中则进入 `orphan_requests`。

---

## 推荐执行步骤（给 Agent）

1. 检查输入 zip 是否存在，并确认输出目录可写。
2. 用 `.venv` Python 执行 `parse_trace.py` 生成 JSON。
3. 如需便于人工检查，同时加 `--markdown-out`。
4. 返回输出文件路径与关键统计：
   - action 数量
   - orphan 请求数量
   - diagnostics 条数

---

## 命令模板

```powershell
.\.venv\Scripts\python "demo/trace_click_api/parse_trace.py" `
  --zip "demo/trace_click_api/traces/task_trace.zip" `
  --lookahead 1500 `
  --json-out "demo/trace_click_api/out/trace_report.json" `
  --markdown-out "demo/trace_click_api/out/trace_report.md"
```

---

## 常见问题与处理

| 现象 | 排查建议 |
|------|----------|
| `zip 中未找到 trace.trace` | 检查输入是否真的是 Playwright trace.zip，或 zip 内结构是否异常 |
| JSON 里请求很少 | 检查是否过滤掉了 document/静态资源，可尝试 `--include-document` |
| 请求都进 orphan | 增大 `--lookahead`，或关闭下一操作截断（`--no-next-cap`） |
| 末尾接口缺失 | 回到 trace 录制阶段，保证 `context.tracing.stop()` 前等待收尾完成 |

---

## 输出 JSON 结构（关键字段）

```json
{
  "meta": { "zip_path": "..." },
  "diagnostics": [],
  "actions": [
    {
      "index": 0,
      "api_name": "Frame.click",
      "params": {},
      "window": { "lower": 0, "upper": 0 },
      "matched_requests": []
    }
  ],
  "orphan_requests": [],
  "params": { "lookahead_ms": 1500.0, "use_next_action_cap": true }
}
```
