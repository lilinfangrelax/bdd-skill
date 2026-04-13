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

### Step 2 — Parse the requirements

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

### Step 3 — Generate the `.feature` file

Follow the Gherkin conventions in `references/gherkin-rules.md`.

Always produce:
- One `Feature:` block with a description
- At least **3 Scenario types**: happy path, sad path, edge case
- `Scenario Outline` + `Examples:` for data-driven cases (boundary values, multiple inputs)
- Chinese or English — match the language of the source requirements

**Prompt template to use internally:**

```
你是资深 QA 工程师，精通 BDD。

请将以下需求转换为标准 Gherkin 格式的 .feature 文件。

规则：
1. Feature 块包含简短的业务描述（2-3 句）
2. 覆盖：正常流程（Happy Path）、异常流程（Sad Path）、边界条件（Edge Case）
3. 步骤用业务语言，不暴露技术实现（不写 API、数据库、mock 等）
4. 数据驱动的场景用 Scenario Outline + Examples
5. 每个 Scenario 只验证一个行为
6. 语言与需求文档一致（中文需求 → 中文 Gherkin）
7. 只输出 Gherkin 代码，不加解释

需求：
<REQUIREMENTS_CONTENT>
```

### Step 4 — Write the output file

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

### Step 5 — Offer Step Definition skeleton

After generating the `.feature` file, always ask:

> "是否需要同时生成对应的 Step Definitions 骨架？支持 pytest-bdd（Python）、Cucumber（Java/JS）或 Behave（Python）。"

If yes, read `references/step-def-templates.md` and generate the skeleton.

---

## Quality checklist (run before outputting)

- [ ] Feature description explains the business value, not the technical spec
- [ ] Every `Given` sets up state, not an action
- [ ] Every `When` is a single user action
- [ ] Every `Then` checks a visible/verifiable outcome
- [ ] No technical terms (API, DB, mock, HTTP 200) in steps
- [ ] `Scenario Outline` used for 3+ similar cases with different data
- [ ] At least one sad path per major happy path
- [ ] Steps are reusable across scenarios (no one-off phrasing)

---

## Reference files

- `references/gherkin-rules.md` — Gherkin syntax rules and anti-patterns  
- `references/step-def-templates.md` — Step definition templates for pytest-bdd / Cucumber / Behave

Read these when you need detailed guidance on syntax or step generation.
