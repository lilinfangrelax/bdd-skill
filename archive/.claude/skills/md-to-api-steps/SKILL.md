---
name: md-to-api-steps
description: >
  根据用户勾选后的 BDD 确认 MD 文件和原始 trace.zip，按需提取真实 request/response body，
  自动推断接口间数据依赖（ctx 变量），生成 API 自动化测试步骤的 Markdown 文件。
  当用户提到"根据选好的接口生成自动化步骤"、"md 转 api steps"、"生成接口自动化测试用例"时，务必使用此 skill。
  输入：① 用户勾选后的 bdd_confirmed.md  ② 原始 trace.zip。
  输出：api_steps.md，每个 step 含真实 Request / Response body 及 ctx 依赖标注。
---

# MD → API Steps Skill

## 输入规范

| 输入 | 说明 |
|------|------|
| `bdd_confirmed.md` | 用户已勾选的 BDD 确认文件，`[x]` = 纳入自动化，`[]` = 跳过 |
| `trace.zip` | Playwright 录制回放生成的原始 trace 文件 |

### bdd_confirmed.md 格式约定

```markdown
## Step 2：新增任务

- [x] `POST` http://host/api/tasks/create → ✅ 201   ← 纳入
- []  `GET`  http://host/api/tasks → ✅ 200           ← 跳过
```

---

## 核心算法

### Step 1：解析 MD，提取 [x] 选中项

```
逐行扫描：
  - `## Step N：label`  → 记录当前 step_index / step_label
  - `- [x] \`METHOD\` URL` → 提取 method、url、status，归属当前 step
  - `- [] ...`           → 跳过
```

### Step 2：从 trace.zip 按需提取 body

trace.zip 内部结构：
```
trace.zip
├── trace.network     ← NDJSON，每行一个 resource-snapshot
└── resources/
    └── <sha1>.json   ← 真实 request / response body
```

`trace.network` 中 body 不 inline，通过 sha1 引用：
```
snapshot.request.postData._sha1      → request body 文件名
snapshot.response.content._sha1     → response body 文件名
```

匹配逻辑：
```python
key = f"{method}:{url}"   # 与 MD 中的 method+url 对齐
snap = network_snapshots[key]
req_body  = read_resource(zip, snap.request.postData._sha1)
resp_body = read_resource(zip, snap.response.content._sha1)
```

### Step 3：ctx 依赖推断

启发规则：
- 路径含 `create` 且 status 2xx → 识别为「生产者」
- 从 `response_body` 提取真实 id 值（`.id` / `.task.id` / `.data.id`）
- 后续 entry 的 `request_body.id` 若等于该值 → 替换为 `{{ctx.<resource>_id}}`
- 资源名从路径推断：`/api/tasks/create` → `task_id`

### Step 4：渲染输出格式

```markdown
## Step N：{step_label}

**METHOD** `{url}`

**Request**
\`\`\`json
{ ... 真实字段，id 已替换为 {{ctx.task_id}} ... }
\`\`\`

**Response**
\`\`\`json
{ ... 真实响应体 ... }
\`\`\`

> 💾 提取 `response` 中的 `id` → 存入 `ctx.task_id`   ← 仅生产者显示
> 🔗 `id` 引用 来自「新增任务」→ `ctx.task_id`          ← 仅消费者显示
```

---

## 执行方式

```bash
python scripts/md_to_api_steps.py <bdd_confirmed.md> <trace.zip> <output.md>
```

**Claude 操作步骤：**

1. 确认两个输入文件路径均可访问
2. 执行脚本，output.md 写入 `/mnt/user-data/outputs/`
3. 用 `present_files` 提供给用户下载

---

## 边界情况

| 情况 | 处理 |
|------|------|
| trace.zip 无 `.network` 文件 | 打印警告，body 留空（`// TODO`） |
| url 在 network 中无匹配 | body 留空 |
| response body sha1 缺失（status -1）| 输出 `// 录制时请求中断` |
| create 响应无法提取 id | ctx 替换跳过，保留原始值 |
| 同一 url 多次出现 | 取 network 中第一次出现（与录制顺序一致） |
