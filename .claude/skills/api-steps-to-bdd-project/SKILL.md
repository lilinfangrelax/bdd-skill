---
name: api-steps-to-bdd-project
description: >
  将 `api_steps.md`（由 md-to-api-steps 生成）解析为 pytest-bdd 可用的 fixture JSON，
  并在目标 `bdd_project` 中追加 API 专用 Scenario、生成 `generated_api_steps.py` 脚手架。
  当用户提到「api_steps 接入 bdd_project」「api_steps 转 feature/fixture」「生成 API BDD 脚手架」时使用。
  输入：① `api_steps.md` ② `bdd_project` 根路径（可选：feature 文件、Scenario 名、fixture 输出路径）。
  输出：`fixtures/api_steps/*.json`、更新后的 `.feature`、以及 `steps/api/generated_api_steps.py`（不自动修改 `test_api.py` / 既有 `steps.py`）。
---

# API Steps → bdd_project Skill

## 输入规范

| 输入 | 说明 |
|------|------|
| `api_steps.md` | MD → API Steps 产物，含二级标题（**推荐** `## 标签`；兼容 `## Step N：标签`）、`**METHOD** \`url\``、**Request**/**Response** JSON 代码块、`> 💾` / `> 🔗` 提示 |
| `bdd_project` 根目录 | 含 `features/`、`fixtures/`、`steps/api/` 的工程路径 |
| 可选参数 | `--feature`、`--scenario-name`、`--fixture-out`、`--steps-out` |

### `api_steps.md` 最小结构

```markdown
## 新增任务

**POST** `http://127.0.0.1:8765/api/tasks/create`

**Request**
```json
{ "name": "..." }
```

**Response**
```json
{ "ok": true, "task": { "id": "uuid-..." } }
```

> 💾 提取 `response` 中的 `id` → 存入 `ctx.task_id`
```

异常/中断步骤：Response 代码块为 `// status: err` 或非合法 JSON 时，生成 `expect_fail: true`。

## 核心算法

1. **按 `---` 或 `##` 二级标题分块**，逐块解析：**step_label**（标题文案，作唯一标识）、method、url。不再依赖「Step 1/2/3」序号；旧格式 `## Step N：标签` 仍可读，但只使用 **标签** 部分。
2. **Request/Response**：读取 ` ```json ` 代码块；Response 若无法解析为 JSON 或含 `status: err` → `expect_fail=true`。
3. **ctx 提取**：正则匹配 `> 💾 .*→ 存入 \`ctx.(\w+)\`` → `ctx_extract_var`。
4. **ID 模板化**：从「生产者」步的响应 JSON 中取出 `task.id` / `id`，将后续所有响应模板中该 UUID 替换为字面量字符串 `{{ctx.task_id}}`（与 request 占位符一致），便于跨运行断言。
5. **HTTP 状态**：非 err 步骤默认 `status_expected: 200`（可在生成后手工改 fixture）。

## 执行方式

```bash
python scripts/api_steps_to_bdd_project.py <api_steps.md> <bdd_project_root> [选项]
```

常用选项：

- `--feature bdd_project/features/task.feature`
- `--scenario-name "用户完整操作任务（API）"`
- `--fixture-out bdd_project/fixtures/api_steps/task_api.json`
- `--steps-out bdd_project/steps/api/generated_api_steps.py`

**操作步骤：**

1. 确认 `api_steps.md` 与 `bdd_project` 路径可访问。
2. 执行脚本生成/覆盖上述产物。
3. **手动接入**：在 `bdd_project/tests/test_api.py` 的 `pytest_plugins` 中增加 `"bdd_project.steps.api.generated_api_steps"`（或按需合并到既有 `steps.py`），并为新 Scenario 增加 `@scenario(...)`。

## 边界情况

| 情况 | 处理 |
|------|------|
| Response 仅为 `// status: err` 注释 | `expect_fail=true`，`response_body_template=null` |
| 无 `💾` 行 | `ctx_extract_var=null` |
| URL 含完整 host | 提取 `path`（含 `/api/...`），运行时由 `HttpClient` 与 `API_BASE_URL`（或默认 `http://localhost:8765`）拼接 |
| 两个步骤标题完全相同 | 应避免；fixture 以 `step_label` 查找，重名会导致歧义 |

生成的 Gherkin 与脚手架使用 **`「step_label」`**（角括号包裹标题）定位步骤，例如：`When 客户端发送 API 请求「新增任务」`。

跨 Step 共享状态使用 pytest fixture **`context`**（生成步骤内定义）；`bdd_project/steps/api/conftest.py` 提供 **`http_client`**（`HttpClient`）与 **`task_api`**（可选显式 API 封装）。
