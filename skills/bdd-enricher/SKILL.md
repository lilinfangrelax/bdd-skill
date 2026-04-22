---
name: bdd-enricher
description: Enrich and improve existing Gherkin BDD .feature files by identifying coverage gaps and generating missing scenarios. Use this skill whenever the user wants to supplement, improve, or complete an existing .feature file — especially when only happy path scenarios exist and sad path / edge cases are missing. Trigger on phrases like "补充用例", "优化BDD", "完善feature文件", "添加异常场景", "enrich feature", "add missing scenarios", "improve test coverage", or whenever a .feature file is provided and the user asks for more scenarios.
---

# BDD Enricher Skill

读取已有的 `.feature` 文件，分析覆盖缺口，自动补充高价值的异常场景、边界条件和业务规则场景，输出增强后的完整 `.feature` 文件。

---

## Workflow

### Step 1 — 读取 .feature 文件

用户提供 `.feature` 文件路径。读取并解析全部内容。

```bash
cat "<path-to-existing.feature>"
```

### Step 2 — 盘点现有覆盖（Coverage Inventory）

在脑中建立一张「已有步骤清单」，格式如下：

```
Background Given:
  - <步骤文本>

已有 Scenario 列表:
  - [Happy/Sad/Edge] <Scenario 名称>
      Given: <步骤列表>
      When:  <步骤列表>
      Then:  <步骤列表>

已出现的完整步骤池:
  - Given: [...]
  - When:  [...]
  - Then:  [...]
```

这张清单贯穿后续所有步骤，用于去重和复用判断。

### Step 3 — 识别覆盖缺口（Gap Analysis）

对照 `references/gap-analysis-checklist.md` 中的分析框架，逐类检查缺失项。

输出一份**缺口清单**给用户确认，格式：

```
📋 覆盖缺口分析

✅ 已覆盖
  - Happy Path: 正常登录流程

❌ 未覆盖（建议补充）
  [SAD-1]  密码错误 → 尚未覆盖
  [SAD-2]  账号被锁定时尝试登录 → 尚未覆盖
  [EDGE-1] 手机号格式非法（前端拦截）→ 尚未覆盖
  [BIZ-1]  连续失败5次触发锁定机制 → 尚未覆盖

⚠️  可选补充（价值较低，视团队决策）
  [ENV-1]  网络超时时的降级提示
  [CONC-1] 同一账号多端同时登录

共识别到 4 个高价值缺口，2 个可选缺口。
是否全部补充，还是只补充高价值部分？（回复"全部" / "仅高价值" / 指定编号）
```

等待用户确认后再进入 Step 4。

### Step 4 — 生成补充 Scenario

根据用户选择的缺口，按照以下规则生成新 Scenario，并将结果追加到原文件的对应分组下。

**生成规则（严格遵守）：**

```
你是资深 QA 工程师，精通 BDD。

已有 .feature 文件内容：
<EXISTING_FEATURE_CONTENT>

已有步骤池（Given / When / Then 分别列出）：
<EXISTING_STEPS_POOL>

需要补充的缺口：
<GAP_LIST>

生成规则：
1. 【禁止重复】不得生成与已有 Scenario 语义相同的场景
2. 【禁止重复 Background】Scenario 的 Given 不得包含 Background 中已有的步骤
3. 【优先复用步骤】新 Scenario 的 Given/When 步骤，优先从已有步骤池中选取；
   只有语义确实不同时才新增步骤；不得因"措辞更清晰"而创造重复步骤
4. 【一个 Scenario 一个行为】每个 Scenario 只验证一个失败原因或边界条件
5. 【业务语言】步骤不暴露技术实现（不写 API、DB、mock、HTTP 状态码）
6. 【数据驱动】同类边界值（如多种非法格式）用 Scenario Outline + Examples 合并
7. 【语言一致】与原文件保持相同语言（中文/英文）
8. 只输出新增的 Scenario 块，不重复已有内容
```

### Step 5 — 合并输出

将新 Scenario 插入原文件的正确位置：

```
Feature: ...
  Background: ...        ← 保持不变

  # ── Happy Path ──     ← 原有场景保持不变
  Scenario: ...

  # ── Sad Path ──       ← 新增分组（如原来没有）
  Scenario: ...（新增）
  Scenario: ...（新增）

  # ── Edge Case ──      ← 新增分组
  Scenario Outline: ...（新增）

  # ── 业务规则 ──        ← 新增分组（如有）
  Scenario: ...（新增）
```

将合并后的完整文件写入磁盘，覆盖原文件或写入 `<原文件名>_enriched.feature`（询问用户偏好）。

```bash
cat > "<output-path>.feature" << 'EOF'
<merged full feature content>
EOF
```

然后用 `present_files` 分享文件。

### Step 6 — 输出变更摘要

```
✅ 补充完成

原有 Scenario 数：3
新增 Scenario 数：5（其中 Scenario Outline 1 个，覆盖 4 条数据）
复用已有步骤：8 条
新增步骤：3 条

新增场景：
  [SAD-1]  密码错误登录失败
  [SAD-2]  账号锁定期间尝试登录
  [EDGE-1] 手机号格式校验（Scenario Outline，4 种非法格式）
  [BIZ-1]  连续失败5次触发锁定
  [BIZ-2]  锁定30分钟后自动解锁
```

---

## Quality checklist（输出前自查）

**去重**
- [ ] 没有与已有 Scenario 语义相同的新场景
- [ ] 新 Scenario 的 Given 未包含 Background 中已有的步骤

**步骤复用**
- [ ] 新 Scenario 的 Given/When 优先复用了已有步骤池中的步骤
- [ ] 未出现"措辞略有不同但语义相同"的重复步骤

**场景质量**
- [ ] 每个新 Scenario 只验证一个行为
- [ ] 同类边界值已合并为 Scenario Outline
- [ ] Then 步骤描述的是可观测的业务结果，而非内部状态

**完整性**
- [ ] 输出文件包含原有全部 Scenario（未丢失）
- [ ] 新增分组有注释标题（`# ── Sad Path ──` 等）

---

## Reference files

- `references/gap-analysis-checklist.md` — 系统性的缺口识别框架，按场景类型分类列出检查项
