---
name: jinja2-template-gen
description: >
  生成符合 Jinja2 规范的模板文件，用于将 JSON 数据渲染成目标文本。
  必须在以下场景触发此 Skill：用户需要将 JSON 字符串中的字段进行变量替换、条件替换、循环渲染，
  或者需要将现有 Agent 生成的 Jinja2 文件进行规范化整改（补充默认值、修复 undefined 问题、统一排版）。
  关键词：jinja2、j2 模板、模板渲染、变量替换、undefined、StrictUndefined、default 过滤器、
  JSON 转模板、模板文件生成、条件替换。即使用户只说"帮我生成一个 jinja2 文件"也应触发此 Skill。
---

# Jinja2 Template Generator Skill

## 背景与目标

本 Skill 专为如下场景设计：
- 输入：一段 JSON 字符串（含需要替换的字段）+ 可能存在的现有 `.j2` 参考文件
- 输出：一个规范、健壮的 `.j2` Jinja2 模板文件
- 渲染环境约束：`undefined=StrictUndefined`，`autoescape=False`

---

### 核心问题诊断

#### ⚠️ 陷阱一：StrictUndefined + `| default()` 的静默失效

`StrictUndefined` 在访问未定义变量时会抛出 `UndefinedError`，**但以下写法会绕过它，导致静默失败**：
- `{{ var | default('fallback') }}` — default 过滤器在求值前拦截了 Undefined，不会报错
- `{% if var is defined %}` — `is defined` 测试不会触发 StrictUndefined
- `{{ var | default('', boolean=True) }}` — 同上

**后果**：模板里所有变量都加了 `| default()`，`StrictUndefined` 形同虚设，变量真正缺失时没有任何报错。

#### ⚠️ 陷阱二：`| mandatory` 不是标准 Jinja2 内置过滤器

`| mandatory` 来自 **Ansible**，标准 Jinja2 环境中不存在此过滤器，直接使用会报 `FilterModule not found`。

**必须在创建 Jinja2 Environment 时手动注册**：

```python
from jinja2 import Environment, StrictUndefined, UndefinedError

def mandatory_filter(value, msg='该变量为必填项'):
    """自定义 mandatory 过滤器：变量缺失或为 None 时抛出错误"""
    from jinja2 import Undefined
    if isinstance(value, Undefined) or value is None:
        raise UndefinedError(msg)
    return value

env = Environment(
    undefined=StrictUndefined,
    autoescape=False,
)
env.filters['mandatory'] = mandatory_filter
```

> 如果渲染环境**无法修改**（不能注册自定义 filter），则对必填变量直接裸用（不加任何 filter），依赖 StrictUndefined 自然触发错误：
> ```jinja2
> {{ order_id }}   {# 缺失时 StrictUndefined 会抛 UndefinedError #}
> ```

#### ⚠️ 陷阱三：`None`（JSON null）与 `undefined` 是两种状态

| 情况 | `var is defined` | `var` 的布尔值 |
|------|-----------------|--------------|
| 变量不存在于上下文 | `False` | StrictUndefined 抛错 |
| 变量存在，值为 `None`（JSON null） | **`True`** | `False`（falsy） |
| 变量存在，值为空字符串 `""` | `True` | `False`（falsy） |

**结论**：`{% if var is defined and var %}` 能同时过滤"不存在"和"null/空字符串"两种情况，是可选块的正确写法。但如果需要**区分** null 和 undefined，需要使用 `{% if var is defined and var is not none %}`。

---

## 执行流程

### Step 1：扫描现有参考文件

优先查找仓库中现有的 `.j2` / `.jinja2` / `.jinja` 文件作为风格参考：

```bash
find . -name "*.j2" -o -name "*.jinja2" -o -name "*.jinja" 2>/dev/null | head -20
```

阅读找到的参考文件，提取以下信息：
- 缩进风格（2空格 / 4空格）
- 变量注释惯例（文件头是否有变量清单）
- 空白控制风格（是否使用 `{%- -%}`）
- 复杂逻辑的组织方式（macro、block、include 等）

若无参考文件，使用本 Skill 的默认规范（见下方）。

---

### Step 2：分析 JSON 输入，分类变量

仔细分析 JSON 中所有字段，按以下维度分类：

| 类型 | 判断依据 | 模板处理方式 |
|------|----------|-------------|
| **必填变量** | 缺失时业务逻辑无法执行（如 ID、名称） | `{{ var \| mandatory('错误说明') }}` 或裸变量（依赖 StrictUndefined） |
| **可选变量（有合理默认值）** | 缺失或 null 时均可用占位值 | `{{ var \| default('默认值', boolean=True) }}` |
| **可选变量（仅缺失时用默认，null 需保留）** | None 有语义意义 | `{{ var \| default('默认值') }}` |
| **可选变量（缺失时应跳过整个块）** | 整段内容是否出现取决于该字段 | `{% if var is defined and var %}...{% endif %}` |
| **布尔/枚举条件** | 用于控制输出分支 | `{% if var == 'value' %}...{% elif %}...{% endif %}` |
| **列表/数组** | JSON array 字段 | `{% for item in var %}...{% endfor %}` |
| **循环内累积状态** | 在 for 循环内更新变量 | `{% set ns = namespace(val=init) %}`（⚠️ 普通 set 不会泄露出循环） |

---

### Step 3：编写模板文件

严格遵循以下规范输出 `.j2` 文件：

#### 3.1 文件头部（必须包含变量清单注释）

```jinja2
{#
  模板名称：xxx.j2
  用途说明：一句话描述本模板的作用

  变量清单：
    必填变量：
      - variable_name  (str)  说明
      - another_var    (int)  说明

    可选变量（含默认值）：
      - opt_var        (str)  说明  默认值: "default"
      - flag_var       (bool) 说明  默认值: false

  渲染环境：StrictUndefined=True, autoescape=False
#}
```

#### 3.2 变量处理规则

**必填变量**——使用 `mandatory`，提供有意义的错误信息：
```jinja2
{{ order_id | mandatory('order_id 是必填字段，请在渲染数据中提供') }}
```

**可选变量（有默认值）**——使用 `default`，默认值须与业务语义匹配：
```jinja2
{{ status | default('pending') }}
{{ retry_count | default(0) }}
{{ tags | default([]) }}
```

**可选块（整段可跳过）**——用 `is defined` + 非空双重判断：
```jinja2
{% if remarks is defined and remarks %}
备注：{{ remarks }}
{% endif %}
```

**严禁**的写法（规避 StrictUndefined 的陷阱）：
```jinja2
{# ❌ 错误：对必填变量使用 default，掩盖缺失问题 #}
{{ order_id | default('') }}

{# ❌ 错误：对可选块变量只用 default 而不用 if，导致空值块仍然输出 #}
{{ remarks | default('') }}

{# ✅ 正确：明确区分必填与可选 #}
{{ order_id | mandatory('order_id 必填') }}
{% if remarks is defined and remarks %}备注：{{ remarks }}{% endif %}
```

#### 3.3 排版规范

```jinja2
{# 1. 块级标签（if/for）独占一行，内容缩进 2 空格（或跟随参考文件风格） #}
{% if condition %}
  内容
{% endif %}

{# 2. 嵌套缩进保持对齐 #}
{% for item in items %}
  {% if item.active %}
    {{ item.name }}
  {% endif %}
{% endfor %}

{# 3. 空白控制：在纯逻辑行（不需要输出换行）使用 {%- -%} #}
{%- if condition -%}
内容
{%- endif -%}

{# 4. 行内条件用三元表达式，简洁且不换行 #}
状态：{{ '激活' if is_active else '停用' }}

{# 5. 复杂逻辑抽取为 macro #}
{% macro format_address(addr) %}
  {{ addr.province }}{{ addr.city }}{{ addr.detail }}
{% endmacro %}
```

#### 3.4 数据类型安全

```jinja2
{# 数字格式化，防止 None 渲染为字符串 "None" #}
{{ price | default(0) | float | round(2) }}

{# 列表遍历，防止 None 导致迭代失败 #}
{% for tag in (tags | default([])) %}
  {{ tag }}
{% endfor %}

{# 字符串操作前确保非空 #}
{% if name is defined and name is string %}
  {{ name | upper }}
{% endif %}

{# 日期时间格式化 #}
{{ created_at | default('N/A') }}
```

---

### Step 4：自检 Checklist

生成模板文件后，必须逐项确认：

- [ ] **文件头注释**：包含模板用途 + 完整变量清单（必填/可选分开列出）
- [ ] **必填变量**：全部使用 `| mandatory('描述')` 而非 `| default('')`
- [ ] **可选变量**：`default` 的值与业务语义匹配（非空字符串时用 `if` 控制整块）
- [ ] **无裸变量**：不存在既没有 `mandatory` 也没有 `default` 的变量（在 StrictUndefined 下会直接崩溃）
- [ ] **缩进一致**：全文统一使用 2 空格或 4 空格，不混用
- [ ] **空白控制**：纯逻辑行（for/if 的开闭标签）按需使用 `{%- -%}` 避免多余空行
- [ ] **无语法错误**：`{% if %}` 必须有 `{% endif %}`，`{% for %}` 必须有 `{% endfor %}`
- [ ] **风格一致性**：与参考文件的排版风格保持一致

---

### Step 5：输出文件

输出规范的 `.j2` 文件，文件名建议命名为 `<用途描述>.j2`，例如：
- `order_notification.j2`
- `config_render.j2`
- `email_body.j2`

并在对话中附上**简要说明**：
1. 哪些变量被标记为 `mandatory`（必填）及原因
2. 哪些变量使用了 `default`（可选）及默认值
3. 与参考文件相比，有哪些风格对齐或差异

---

## 附录：常见 JSON → Jinja2 映射速查

详见 `references/patterns.md`。

---

## 附录：StrictUndefined 行为速查

| 操作 | 变量不存在 | 变量为 None |
|------|-----------|------------|
| `{{ var }}` | ✅ 抛出错误 | 输出 `None` 字符串 |
| `{{ var \| default('x') }}` | ❌ 静默，返回 `'x'` | ❌ 输出 `None`（default 不处理 None） |
| `{{ var \| default('x', boolean=True) }}` | ❌ 返回 `'x'` | ❌ 返回 `'x'`（None 为 falsy） |
| `{{ var \| mandatory('msg') }}` | ✅ 抛出错误（需注册自定义filter） | ✅ 也会抛错（含自定义消息） |
| `{% if var is defined %}` | ❌ 静默，返回 False | ❌ 返回 True（None 已定义！） |
| `{% if var is defined and var %}` | ❌ 静默，False | ❌ 静默，False（None 为 falsy） |
| `{% if var is defined and var is not none %}` | ❌ 静默，False | ❌ 静默，False（明确排除 None） |
| `{% if var %}` | ✅ 抛出错误 | ❌ 静默，False |
| `{{ var.attr }}` | ✅ 抛出错误 | ✅ 抛出 AttributeError |
| `{% for x in var %}` | ✅ 抛出错误 | ✅ 抛出 TypeError |
| `{% for x in (var \| default([])) %}` | ❌ 静默，空循环 | ❌ 静默，None 不被 default 替换 |

> ⚠️ `| default(value)` **不替换 None**，只替换 `Undefined`。如需同时处理 None，使用 `| default(value, boolean=True)`（当变量为 falsy 时替换，包括 None、""、0、[]）。
