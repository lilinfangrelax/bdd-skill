# Playwright trace.zip：UI 操作与接口请求映射（复用提示词）

> 用途：向 AI 说明 trace 结构、关联思路与难点，用于制定方案或评审实现。  
> 说明：部分字段名因 Playwright 版本而异，实现时需以实际 `trace.trace` / `trace.network` 为准。

---

【目标】解析 trace.zip 文件，得到 UI 操作步骤和接口请求的对应关系，制定方案

Playwright 的 trace 文件本质上是一个 zip 包，解压后结构如下：

```text
trace.zip
├── trace.trace          ← 主事件流（NDJSON 格式，每行一个事件）
├── trace.network        ← 网络请求记录（NDJSON 格式）
├── resources/
│   ├── *.png            ← 每个操作前后的截图
│   └── *.json           ← API 响应体快照（可选）
└── trace.stacks         ← 调用栈信息
```

## 核心数据格式

### trace.trace（UI 操作事件）

每行是一个 JSON 对象，关键字段示例：

```json
{
  "type": "action",
  "startTime": 1700000001234,
  "endTime": 1700000001456,
  "apiName": "page.click",
  "params": {
    "selector": "#login-btn",
    "strict": true
  },
  "wallTime": 1700000001234,
  "callId": "call@1"
}
```

常见的 apiName 类型：

- page.click / page.fill / page.goto
- locator.click / locator.fill
- expect.toBeVisible 等断言

### trace.network（接口请求）

```json
{
  "type": "resource",
  "startTime": 1700000001300,
  "endTime": 1700000001400,
  "url": "https://api.example.com/v1/login",
  "method": "POST",
  "status": 200,
  "requestHeaders": [],
  "responseHeaders": [],
  "requestBody": "...",
  "responseBody": "..."
}
```

## 关联逻辑：如何建立 UI 操作 ↔ 接口请求的映射

核心思路是**时间窗口匹配**：

```text
UI Action [startTime ──────── endTime]
                    ↑
          Network Request [startTime ── endTime]

          如果 request.startTime 在 action 的时间窗口内
          → 认为该请求由该操作触发
```

## 潜在难点与对策

| 难点 | 说明 | 对策 |
|------|------|------|
| **时间窗口模糊** | 一个操作可能触发多个请求，或请求跨越多个操作 | 引入「主请求」判断（如 XHR/fetch，排除静态资源） |
| **异步延迟** | 操作结束后请求才发出 | `lookahead_ms` 参数调优，或用下一个操作的 startTime 作为窗口上限 |
| **trace 格式版本** | Playwright 不同版本的字段名可能有差异 | 固定 Playwright 版本，或做兼容处理 |
| 心跳信息/重复包 | 有一些定时发送过来的资源，并不是由操作触发的 | 过滤 |

最大的工作量在于时间窗口关联策略的调优，以及对静态资源的过滤。
