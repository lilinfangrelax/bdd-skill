---
name: req-to-bdd
description: Convert requirements text files into Gherkin BDD .feature files. Use this skill whenever the user mentions converting requirements, user stories, or specs to BDD, Gherkin, feature files, or test scenarios. Also trigger when the user provides a .txt file and asks for test cases, BDD scenarios, or feature files. Trigger even if the user just says "generate BDD" or "create feature file" without a full explanation.
---

# Req → BDD Skill

Convert a requirements `.txt` file into a well-structured Gherkin `.feature` file, ready for pytest-bdd, Cucumber, or Behave.

---

## Workflow

### Step 1 — Locate the input file

The user will provide a `.txt` file path (absolute or relative). If not provided, ask for it.

```bash
# Confirm file exists
cat "<path-to-requirements.txt>"
```

If the file is in `/mnt/user-data/uploads/`, read it from there directly.

### Step 2 — Diagnose input quality

Before parsing, evaluate the requirement text against these quality signals. **Do not skip this step.**

| Signal | Good | Poor (needs repair) |
|--------|------|---------------------|
| 角色明确 | "注册用户可以..." | "用户可以..."（哪类用户？） |
| 动作可测试 | "点击提交后跳转到首页" | "系统处理请求"（处理了什么？） |
| 结果可观测 | "显示错误提示'密码错误'" | "提示用户"（提示什么？） |
| 业务规则数字化 | "连续失败5次锁定30分钟" | "多次失败后锁定"（多少次？多久？） |
| 边界条件有说明 | "手机号必须为11位数字" | "手机号格式正确"（什么才算正确？） |

**If 2 or more signals are poor**, pause and output a **需求诊断报告** before generating any Gherkin:

```
⚠️ 需求质量诊断

发现以下描述不够明确，可能影响 BDD 用例的准确性：

1. [引用原文] → 问题：缺少具体的错误提示文案，无法生成 Then 步骤
2. [引用原文] → 问题：未说明边界值，建议补充（如：最大长度、允许的字符类型）
3. [引用原文] → 问题：角色模糊，"用户"指已登录用户还是访客？

建议补充后重新生成，或回复"继续"让我根据常见业务惯例进行合理推断。
```

Wait for the user to reply. If they say "继续" or similar, proceed with inference and **annotate each inferred assumption** inline in the `.feature` file as a `# [推断]` comment.

### Step 3 — Parse the requirements

Read the file content. Identify:
- **Actors / Roles** — who is using the system?
- **Features / Functions** — what can they do?
- **Business rules** — constraints, limits, conditions
- **Implicit edge cases** — what can go wrong?

Use this mental checklist before writing any Gherkin:

| Category | Questions to ask |
|----------|-----------------|
| Happy path | What is the normal, successful flow? |
| Sad path | What happens when input is invalid or action fails? |
| Edge case | Boundary values, timeouts, concurrency, empty states? |
| Business rule | Are there numeric limits, time limits, role restrictions? |

### Step 4 — Generate the `.feature` file

Follow the Gherkin conventions in `references/gherkin-rules.md`.

Always produce:
- One `Feature:` block with a description
- At least **3 Scenario types**: happy path, sad path, edge case
- `Scenario Outline` + `Examples:` for data-driven cases (boundary values, multiple inputs)
- Chinese or English — match the language of the source requirements

**Generation rules (apply strictly):**

```
你是资深 QA 工程师，精通 BDD。

请将以下需求转换为标准 Gherkin 格式的 .feature 文件。

【基本规则】
1. Feature 块包含简短的业务描述（2-3 句）
2. 覆盖：正常流程（Happy Path）、异常流程（Sad Path）、边界条件（Edge Case）
3. 步骤用业务语言，不暴露技术实现（不写 API、数据库、mock 等）
4. 数据驱动的场景用 Scenario Outline + Examples
5. 每个 Scenario 只验证一个行为
6. 语言与需求文档一致（中文需求 → 中文 Gherkin）
7. 只输出 Gherkin 代码，不加解释

【Background 去重规则 - 必须遵守】
- 若使用 Background，先列出所有 Background 中的 Given 步骤
- Scenario 内的 Given 步骤不得与 Background 中的 Given 重复
- 仅将"所有 Scenario 都需要的前提条件"放入 Background
- 若某个前提只属于部分 Scenario，保留在该 Scenario 内，不放 Background

【步骤复用规则 - 必须遵守】
- 生成 Sad Path / Edge Case 之前，先列出已有的所有步骤（来自 Happy Path）
- Sad Path / Edge Case 的 Given / When 步骤，优先从已有步骤中选取，完全相同或只有参数不同时直接复用
- 只有在语义确实不同时，才允许新增步骤
- 禁止为了"看起来更清晰"而创造措辞略有不同的重复步骤

【生成顺序】
1. 先确定 Background（如有）
2. 写 Happy Path Scenario，提取出完整步骤列表
3. 写 Sad Path，每个 Given/When 先对比已有步骤列表再决定新增还是复用
4. 写 Edge Case（同上）

需求：
<REQUIREMENTS_CONTENT>
```

### Step 5 — Write the output file

Determine the output filename:
- If input is `login.txt` → output `login.feature`
- If input is `user_registration_requirements.txt` → output `user_registration.feature`
- Place the `.feature` file in the **same directory** as the input file, unless the user specifies otherwise

```bash
# Write the feature file
cat > "<output-path>.feature" << 'EOF'
<generated gherkin>
EOF
```

Then use `present_files` to share the result.

### Step 6 — Offer Step Definition skeleton

After generating the `.feature` file, always ask:

> "是否需要同时生成对应的 Step Definitions 骨架？支持 pytest-bdd（Python）、Cucumber（Java/JS）或 Behave（Python）。"

If yes, read `references/step-def-templates.md` and generate the skeleton.

---

## Quality checklist (run before outputting)

**基本格式**
- [ ] Feature description explains the business value, not the technical spec
- [ ] Every `Given` sets up state, not an action
- [ ] Every `When` is a single user action
- [ ] Every `Then` checks a visible/verifiable outcome
- [ ] No technical terms (API, DB, mock, HTTP 200) in steps
- [ ] `Scenario Outline` used for 3+ similar cases with different data
- [ ] At least one sad path per major happy path

**Background 去重（新）**
- [ ] Background 中的 Given 步骤未在任何 Scenario 的 Given 中重复出现
- [ ] Background 只包含所有 Scenario 都共享的前提条件

**步骤复用（新）**
- [ ] Sad Path 的 Given/When 步骤已优先复用 Happy Path 中的已有步骤
- [ ] Edge Case 的 Given/When 步骤已优先复用已有步骤
- [ ] 未出现"措辞略有不同但语义相同"的重复步骤

**输入质量（新）**
- [ ] 需求中模糊的描述已被诊断并标注为 `# [推断]` 注释，或已请用户补充

---

## Reference files

- `references/gherkin-rules.md` — Gherkin syntax rules and anti-patterns  
- `references/step-def-templates.md` — Step definition templates for pytest-bdd / Cucumber / Behave

Read these when you need detailed guidance on syntax or step generation.
