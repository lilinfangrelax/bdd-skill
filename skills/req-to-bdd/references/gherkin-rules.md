# Gherkin Rules & Anti-patterns

## Keywords

| Keyword | Purpose | Rule |
|---------|---------|------|
| `Feature:` | Groups related scenarios | One per file; include a 1-3 line business description |
| `Background:` | Shared preconditions | Use only when ≥3 scenarios share the same Given steps |
| `Scenario:` | Single test case | One behavior per scenario |
| `Scenario Outline:` | Parameterized scenario | Use when ≥3 rows of similar data exist |
| `Given` | System state setup | Past tense or present state ("the user is logged in") |
| `When` | User action | Single action only; active voice ("the user clicks") |
| `Then` | Expected outcome | Observable result; never internal state ("the DB has...") |
| `And` / `But` | Continue previous keyword | Same type as the keyword it follows |
| `Examples:` | Data table for Outline | Column names match `<placeholder>` in steps |

---

## ✅ Good patterns

```gherkin
Feature: 用户手机号注册
  作为新用户
  我希望通过手机号完成注册
  以便使用平台的所有功能

  Background:
    Given 系统处于正常运行状态

  Scenario: 使用有效手机号成功注册
    Given 手机号 "13800138000" 尚未注册
    When  用户提交注册信息
    Then  系统创建新账号
    And   页面显示"注册成功"

  Scenario: 使用已注册手机号注册失败
    Given 手机号 "13800138000" 已经注册
    When  用户使用该手机号提交注册
    Then  系统提示"该手机号已注册，请直接登录"

  Scenario Outline: 手机号格式校验
    When  用户输入手机号 "<phone>"
    Then  系统显示提示 "<message>"

    Examples:
      | phone        | message        |
      | 1380013800   | 手机号格式不正确 |
      | abc12345678  | 手机号格式不正确 |
      | 13800138000  | 验证码已发送    |
```

---

## ❌ Anti-patterns

### 1. 技术实现泄漏
```gherkin
# 错误
Then  数据库 users 表新增一条记录
Then  POST /api/v1/register 返回 HTTP 200

# 正确
Then  系统创建新账号
Then  注册请求处理成功
```

### 2. 一个 When 多个动作
```gherkin
# 错误
When  用户填写手机号、验证码并点击注册按钮

# 正确
When  用户填写手机号和验证码
And   用户点击"注册"按钮
```

### 3. Then 检查内部状态
```gherkin
# 错误
Then  session 中 user_id 被设置为 42
Then  Redis 缓存被清除

# 正确
Then  用户进入个人主页
Then  登录状态保持有效
```

### 4. 过度合并场景
```gherkin
# 错误 — 一个 Scenario 测多个行为
Scenario: 注册和登录
  Given ...
  When 用户注册
  Then 注册成功
  When 用户登录
  Then 登录成功

# 正确 — 拆分为独立 Scenario
```

### 5. 缺少 Sad Path
```gherkin
# 需求中有"失败"规则时，必须补充：
Scenario: 密码错误时登录失败
Scenario: 连续失败5次后账号锁定
```

---

## Scenario 命名规范

格式：`[动作] + [条件/上下文] + [结果]`

```
✅ 使用有效手机号成功注册
✅ 验证码过期后注册失败
✅ 超过最大重试次数时账号被锁定
❌ 测试注册功能
❌ 手机号测试
```

---

## Scenario Outline 使用判断

满足以下任一条件时使用 Outline：
- 同一流程需要用 **3 个以上不同数据** 验证
- 有明显的边界值（最小值、最大值、刚好超出）
- 有多种等价类需要覆盖（合法格式、非法格式、空值）
