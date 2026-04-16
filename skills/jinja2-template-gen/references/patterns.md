# JSON → Jinja2 常见映射模式

## 1. 简单字符串字段

**JSON**:
```json
{ "title": "Hello World", "subtitle": null }
```

**模板**:
```jinja2
{{ title | mandatory('title 必填') }}
{% if subtitle is defined and subtitle %}
副标题：{{ subtitle }}
{% endif %}
```

---

## 2. 数字字段

**JSON**:
```json
{ "price": 99.9, "discount": null, "quantity": 1 }
```

**模板**:
```jinja2
单价：{{ price | mandatory('price 必填') | float | round(2) }}
数量：{{ quantity | default(1) | int }}
{%- if discount is defined and discount %}
折扣：{{ discount | float | round(2) }}
{%- endif %}
```

---

## 3. 布尔/枚举条件

**JSON**:
```json
{ "status": "active", "is_vip": true }
```

**模板**:
```jinja2
状态：{{ '激活' if status == 'active' else ('停用' if status == 'inactive' else status | default('未知')) }}
{% if is_vip | default(false) %}
[VIP 会员]
{% endif %}
```

---

## 4. 嵌套对象

**JSON**:
```json
{
  "user": {
    "name": "张三",
    "email": "zhangsan@example.com",
    "address": { "city": "北京", "detail": null }
  }
}
```

**模板**:
```jinja2
{# user 对象本身为必填 #}
{%- set user = user | mandatory('user 对象必填') -%}
用户名：{{ user.name | mandatory('user.name 必填') }}
邮箱：{{ user.email | default('未填写') }}
{%- if user.address is defined %}
城市：{{ user.address.city | default('未知') }}
  {%- if user.address.detail is defined and user.address.detail %}
详细地址：{{ user.address.detail }}
  {%- endif %}
{%- endif %}
```

---

## 5. 数组/列表

**JSON**:
```json
{ "items": [{"name": "商品A", "qty": 2}, {"name": "商品B", "qty": 1}] }
```

**模板**:
```jinja2
{%- set items = items | mandatory('items 列表必填') -%}
{% if items | length == 0 %}
（无商品）
{% else %}
  {% for item in items %}
  {{ loop.index }}. {{ item.name | mandatory('item.name 必填') }} x{{ item.qty | default(1) }}
  {% endfor %}
{% endif %}
```

---

## 6. 可选的整个区块

**JSON**:
```json
{ "notes": "请尽快处理", "attachments": [] }
```

**模板**:
```jinja2
{% if notes is defined and notes %}
---
备注
{{ notes }}
---
{% endif %}

{% if attachments is defined and attachments | length > 0 %}
附件列表：
  {% for att in attachments %}
  - {{ att }}
  {% endfor %}
{% endif %}
```

---

## 7. 字典/映射（动态键）

**JSON**:
```json
{ "metadata": { "env": "prod", "region": "cn-north" } }
```

**模板**:
```jinja2
{% if metadata is defined and metadata %}
元数据：
  {% for key, value in metadata.items() %}
  {{ key }}: {{ value }}
  {% endfor %}
{% endif %}
```

---

## 8. 日期时间字段

**JSON**:
```json
{ "created_at": "2024-01-15T10:30:00", "expired_at": null }
```

**模板**:
```jinja2
创建时间：{{ created_at | mandatory('created_at 必填') }}
{%- if expired_at is defined and expired_at %}
过期时间：{{ expired_at }}
{%- else %}
过期时间：永不过期
{%- endif %}
```

---

## 9. 条件替换（多分支）

**JSON**:
```json
{ "order_type": "express", "payment_method": "wechat" }
```

**模板**:
```jinja2
{% set order_type = order_type | mandatory('order_type 必填') %}
配送方式：
{%- if order_type == 'express' %} 加急快递
{%- elif order_type == 'standard' %} 标准快递
{%- elif order_type == 'pickup' %} 自提
{%- else %} {{ order_type }}（未知类型）
{%- endif %}

支付方式：
{%- set pm = payment_method | default('offline') %}
{%- if pm == 'wechat' %} 微信支付
{%- elif pm == 'alipay' %} 支付宝
{%- elif pm == 'offline' %} 线下支付
{%- else %} {{ pm }}
{%- endif %}
```

---

## 10. Macro 复用

```jinja2
{# 定义可复用的地址格式化 macro #}
{% macro render_address(addr, label='地址') %}
  {%- if addr is defined and addr %}
{{ label }}：{{ addr.province | default('') }}{{ addr.city | default('') }}{{ addr.detail | default('') }}
  {%- endif %}
{% endmacro %}

{# 使用 macro #}
{{ render_address(sender_address, '发件地址') }}
{{ render_address(receiver_address, '收件地址') }}
```

---

## 12. loop 特殊变量（首尾处理、分隔符）

**场景**：列表渲染时需要处理首尾元素（如加分隔符、标记第一项）。

```jinja2
{%- set items = items | mandatory('items 必填') -%}
{% for item in items %}
  {%- if loop.first %}=== 开始 ==={% endif %}
  {{ loop.index }}. {{ item.name }}
  {%- if not loop.last %},{% endif %}   {# 逗号分隔，最后一项不加 #}
  {%- if loop.last %}=== 结束 ==={% endif %}
{% endfor %}
{# loop.index: 从1开始 | loop.index0: 从0开始 | loop.length: 总数 #}
{# loop.cycle('A','B'): 每次循环交替返回值（如奇偶行） #}
```

**`| join` 简洁写法**（适合行内列表，不需要块级处理）：
```jinja2
{# 列表直接转逗号分隔字符串 #}
标签：{{ tags | mandatory('tags 必填') | join('、') }}

{# 提取对象列表中的某个字段，再 join #}
参与者：{{ members | map(attribute='name') | join(' / ') }}
```

---

## 13. 列表过滤与变换（selectattr / rejectattr / map / sort）

**JSON**:
```json
{
  "products": [
    {"name": "A", "active": true, "price": 30},
    {"name": "B", "active": false, "price": 10},
    {"name": "C", "active": true, "price": 20}
  ]
}
```

**模板**:
```jinja2
{%- set products = products | mandatory('products 必填') -%}

{# 只输出激活的商品，按价格升序 #}
{% for p in products | selectattr('active') | sort(attribute='price') %}
  {{ p.name }}: ¥{{ p.price }}
{% endfor %}

{# 排除下架商品的名称列表 #}
在售商品：{{ products | selectattr('active') | map(attribute='name') | join('、') }}

{# 下架商品 #}
下架商品：{{ products | rejectattr('active') | map(attribute='name') | join('、') }}

{# 按 active 状态分组 #}
{% for group in products | groupby('active') %}
{{ '在售' if group.grouper else '下架' }}：{{ group.list | map(attribute='name') | join(', ') }}
{% endfor %}
```

---

## 14. 循环内累积状态（namespace）

**场景**：在 for 循环内修改变量，循环外读取结果。
> ⚠️ 普通 `{% set found = true %}` 在 for/if 块内**不会泄露**到外部作用域，这是 Jinja2 的设计行为。

```jinja2
{# ❌ 错误写法：set 不泄露，循环结束 found 仍为 false #}
{% set found = false %}
{% for item in items %}
  {% if item.id == target_id %}{% set found = true %}{% endif %}
{% endfor %}
结果：{{ found }}  {# 永远输出 false #}

{# ✅ 正确写法：使用 namespace #}
{% set ns = namespace(found=false, total=0) %}
{% for item in items %}
  {% if item.id == target_id %}{% set ns.found = true %}{% endif %}
  {% set ns.total = ns.total + item.price | default(0, boolean=True) | float %}
{% endfor %}
是否找到：{{ ns.found }}
总价：{{ ns.total | round(2) }}
```

---

## 15. 字符串处理过滤器

```jinja2
{# trim: 去除首尾空白 #}
{{ user_input | default('') | trim }}

{# replace: 字符串替换 #}
{{ content | replace('\n', '<br>') }}

{# truncate: 超长截断（默认255字符，保留末尾省略号） #}
{{ description | default('') | truncate(100, killwords=False, end='...') }}

{# upper / lower / title / capitalize #}
{{ name | default('') | title }}

{# wordwrap: 按字数换行 #}
{{ long_text | default('') | wordwrap(80) }}

{# indent: 为多行文本每行添加缩进（第一行可选） #}
{{ multiline_content | default('') | indent(4, first=True) }}

{# tojson: 将 Python 对象序列化为 JSON 字符串（处理特殊字符） #}
配置：{{ config | default({}) | tojson }}
```

---

## 16. 原样输出 Jinja2 语法（raw）

**场景**：模板输出的内容本身包含 `{{ }}`、`{% %}` 语法（如生成另一个模板、Helm chart、Ansible playbook）。

```jinja2
{# 需要在输出中保留 Jinja2 语法时，用 raw 块包裹 #}
以下是 Helm values 模板片段：

{% raw %}
replicas: {{ .Values.replicaCount }}
image:
  repository: {{ .Values.image.repository }}
  tag: {{ .Values.image.tag | default "latest" | quote }}
{% endraw %}

上方内容不会被当前模板引擎解析。
```

---

## 17. 多行文本块赋值（set block）

**场景**：将一段多行内容赋给变量，用于后续条件判断或传参。

```jinja2
{# 用 set...endset 捕获多行文本块 #}
{% set footer_content %}
---
本邮件由系统自动发送，请勿回复。
如有疑问请联系：{{ support_email | default('support@example.com') }}
{% endset %}

{% if show_footer | default(false, boolean=True) %}
{{ footer_content | trim }}
{% endif %}
```

---

## 18. 字典排序输出（dictsort）

**JSON**:
```json
{ "scores": {"张三": 95, "李四": 87, "王五": 92} }
```

**模板**:
```jinja2
{% if scores is defined and scores %}
成绩单（按姓名排序）：
{% for name, score in scores | dictsort %}
  {{ name }}：{{ score }} 分
{% endfor %}

成绩单（按分数降序）：
{% for name, score in scores | dictsort(by='value') | reverse %}
  {{ name }}：{{ score }} 分
{% endfor %}
{% endif %}
```


```jinja2
{# 在模板顶部统一处理可选配置，后续使用局部变量而非直接访问原始变量 #}
{%- set currency = currency | default('CNY') -%}
{%- set lang = language | default('zh-CN') -%}
{%- set debug = debug_mode | default(false) -%}

{% if debug %}[DEBUG 模式已开启]{% endif %}
货币：{{ currency }}
语言：{{ lang }}
```
