---
name: playwright-trace-recorder
description: 将已有 Playwright Python 录制脚本改造成可稳定产出 trace.zip 的执行脚本，并避免 tracing.stop 前因收尾过快导致末尾接口响应丢失。 当用户提到“录制 trace.zip”“Playwright trace”“脚本改造后抓 trace”“trace 最后几条响应没抓到”时使用。
---

# Playwright Trace Recorder

## 适用场景

- 已有 `recording.py`（通常含 `# 注释` 作为 BDD step 标签）
- 需要执行脚本并产出 `trace.zip`
- 需要降低“最后几条请求无响应/未写入 trace”的概率

## 核心原则

1. **尽早启动 trace**：在关键页面动作前执行 `context.tracing.start(...)`。
2. **收尾再 stop**：不要在最后一步动作后立即 `tracing.stop`。
3. **三层等待策略**（默认同时使用）：
   - 等待关键响应（例如保存/提交接口返回 2xx）
   - 等待网络空闲（`page.wait_for_load_state("networkidle")`）
   - 兜底短延时（例如 300~800ms，给 trace flush 缓冲）

## 推荐改造模板（sync API）

```python
from playwright.sync_api import sync_playwright


def run() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # 1) 尽早开始 trace，确保初始化请求也能被记录
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        # ===== 你的录制动作开始 =====
        page.goto("http://127.0.0.1:8765/")

        # 示例：关键请求建议用 expect_response 显式等待
        with page.expect_response(
            lambda r: "/api/tasks/create" in r.url and r.request.method == "POST",
            timeout=15000,
        ) as resp_info:
            page.get_by_role("button", name="新增").click()

        resp = resp_info.value
        if resp.status < 200 or resp.status >= 300:
            raise RuntimeError(f"关键接口失败: {resp.status} {resp.url}")

        # ===== 你的录制动作结束 =====

        # 2) 等待网络收敛，减少末尾请求丢响应
        page.wait_for_load_state("networkidle", timeout=15000)
        # 3) 兜底短等待，给 tracing 写盘留缓冲
        page.wait_for_timeout(500)

        context.tracing.stop(path="trace.zip")
        context.close()
        browser.close()


if __name__ == "__main__":
    run()
```

## 最小改造点（不重写脚本时）

若用户已有脚本结构，只做最小修改：

1. 在创建 `context/page` 后、主要动作前增加：
   - `context.tracing.start(screenshots=True, snapshots=True, sources=True)`
2. 最后一个业务动作后，不要立刻 stop，先加：
   - `page.wait_for_load_state("networkidle", timeout=15000)`
   - `page.wait_for_timeout(500)`
3. 再执行：
   - `context.tracing.stop(path="trace.zip")`

## 关键接口等待建议

- 对“提交/保存/删除/确认”等关键动作，优先使用 `page.expect_response(...)` 包裹触发动作。
- 匹配条件建议包含：`URL 片段 + HTTP 方法`，必要时校验状态码。
- 页面有长轮询/WS 时，`networkidle` 可能不稳定，应以 `expect_response` 为主，`wait_for_timeout` 为辅。

## 执行命令（本项目约束）

在仓库根目录执行，优先使用项目虚拟环境：

```bash
.\.venv\Scripts\python demo/trace_click_api/recordings/task.py
```

若脚本里 `tracing.stop(path="trace.zip")` 使用相对路径，则输出位置为**脚本运行时当前工作目录**。

## 验收检查

- 生成了 `trace.zip`
- 关键接口在 trace 里有 request + response（非 pending）
- 连续执行 2~3 次结果稳定（末尾请求不再随机丢失）

## 与后续 Skill 衔接

产出 `trace.zip` 后，先用解析脚本得到 `trace_parsed.json`，再交给 `trace-to-bdd` skill 生成勾选式 BDD 确认 Markdown。
