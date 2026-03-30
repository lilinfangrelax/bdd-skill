---
name: trace-to-bdd
description: >
  将 Playwright 录制脚本（含 # 注释）与 trace 解析 JSON 合并，自动生成 BDD step ↔ 接口请求的 GFM Markdown 确认文件。
  当用户提到"生成 BDD 步骤"、"trace 转 markdown"、"将录制脚本和 trace JSON 生成 BDD 确认文件"时，务必使用此 skill。
  输入：① Playwright 录制 .py 文件（含 # 注释作为 step 标签）② trace 解析 .json 文件（来自 trace_parser.py）。
  输出：GFM checkbox 格式的 .md 文件，供用户勾选需要纳入自动化的接口。
---

# Trace → BDD Markdown Skill

## 输入规范

| 输入 | 说明 |
|------|------|
| `recording.py` | Playwright 录制脚本，**用 `# 注释` 标注 BDD step**，注释后紧跟该 step 的所有 playwright 调用 |
| `trace_parsed.json` | trace 解析器输出的 JSON，包含 `actions[]` 数组，每个 action 含 `matched_requests[]` |

### recording.py 注释约定

```python
page.goto("http://...")          # goto 前无注释 → 自动归入「打开页面」

# 新增任务                        ← 这行注释 = BDD Step 标签
page.get_by_role(...).click()    # 紧跟注释的 playwright 调用归属此 step
page.get_by_role(...).fill(...)
page.get_by_role(...).click()    # 最后一行触发接口

# 编辑任务                        ← 下一个 Step
page.get_by_role(...).click()
...
```

分隔线 `# ---...` 会被忽略。

### trace_parsed.json 结构（最小必要字段）

```json
{
  "actions": [
    {
      "index": 0,
      "method": "goto",
      "params": { "url": "http://..." },
      "matched_requests": [
        { "method": "GET", "url": "http://.../api/tasks", "status": 200, "network_index": 0 }
      ]
    }
  ]
}
```

---

## 核心算法

### 1. 扫描 py 脚本，统计每个 step 的 playwright 调用数

```
逐行扫描：
  - 遇到 `# 注释`（非分隔线）→ 记录 step label，重置计数器
  - 遇到 `page.*` / `context.*` / `browser.*` 调用 → 计数器 +1
  - 遇到 `# ---` 分隔线 → 忽略

输出：
  pre_calls = goto 前的调用数（隐式「打开页面」step）
  step_counts = [(label, count), ...]
```

### 2. 加载 trace actions，按顺序切片分配

```
actions = trace_parsed.json["actions"]  # 已按 index 排序
idx = 0

if pre_calls > 0:
    「打开页面」step.actions = actions[0 : pre_calls]
    idx += pre_calls

for label, count in step_counts:
    step.actions = actions[idx : idx + count]
    idx += count
```

**关键假设**：py 脚本的 playwright 调用顺序 = trace actions 顺序（录制即回放，天然对齐）。

### 3. 收集每个 step 的接口请求

```python
step.api_calls = [
    req
    for action in step.actions
    for req in action.matched_requests
]
```

### 4. 渲染 GFM Markdown

```markdown
# BDD Steps 确认

勾选需要纳入自动化的接口，取消勾选不需要的。

## Step N：{step.label}

- [x] `{method}` {url} → {icon} {status}
- [x] `{method}` {url} → {icon} {status}
```

状态图标：`✅` = 2xx，`⚠️` = -1（请求未完成），`❌` = 其他错误。

---

## 执行方式

直接运行 `scripts/trace_to_bdd.py`：

```bash
python scripts/trace_to_bdd.py <recording.py> <trace_parsed.json> <output.md>
```

**Claude 操作步骤：**

1. 用 `view` 工具确认两个输入文件路径均可访问
2. 用 `bash_tool` 执行脚本，将 output.md 写入 `/mnt/user-data/outputs/`
3. 用 `present_files` 将 output.md 提供给用户下载

---

## 输出示例

```markdown
# BDD Steps 确认

勾选需要纳入自动化的接口，取消勾选不需要的。

## Step 1：打开页面

- [x] `GET` http://127.0.0.1:8765/api/tasks → ✅ 200

## Step 2：新增任务

- [x] `POST` http://127.0.0.1:8765/api/tasks/create → ✅ 201

## Step 3：编辑任务

- [x] `GET` http://127.0.0.1:8765/api/tasks → ✅ 200
- [x] `POST` http://127.0.0.1:8765/api/tasks/update → ✅ 200
```

---

## 常见边界情况

| 情况 | 处理方式 |
|------|----------|
| goto 前无注释 | 自动创建「打开页面」step，归入 pre_calls 个 actions |
| step 无接口请求 | 输出 `- *(无接口请求)*` |
| status = -1 | 请求中断，显示 `⚠️ err` |
| `# ---` 分隔线 | 正则 `#\s*-{3,}` 匹配，完全忽略 |
| selector 含 unicode escape | `_friendly()` 函数截取前40字符，不影响接口关联 |
