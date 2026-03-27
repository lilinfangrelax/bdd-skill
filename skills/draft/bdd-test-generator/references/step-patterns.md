# 常见 Gherkin 步骤模式库

快速参考：覆盖 80% 场景的步骤写法模板。

---

## 认证 & 权限

```gherkin
# 前置：用户状态
Given 用户未登录
Given 用户已使用账号 "{email}" 登录
Given 用户具有 "{role}" 角色权限
Given 用户的账号处于锁定状态
Given 用户的 Token 已过期

# 动作
When 用户提交登录表单，邮箱 "{email}"，密码 "{password}"
When 用户点击"退出登录"
When 用户访问需要权限的页面 "{url}"

# 断言
Then 用户成功登录，跳转至主页
Then 系统显示错误提示 "{message}"
Then 用户被重定向至登录页
Then 系统返回 HTTP 状态码 {code}
```

---

## 导航

```gherkin
Given 用户在 "{page}" 页面

# 动作
When 去到 "{page}" 页面
```

## 表单 & 数据输入

```gherkin
# 前置
Given 表单所有字段为空

# 动作
When 用户在 "{field}" 字段输入 "{value}"
When 用户清空 "{field}" 字段
When 用户选择下拉选项 "{option}"
When 用户上传文件 "{filename}"
When 用户点击提交按钮
When 用户点击重置按钮

# 断言
Then 页面显示字段 "{field}" 的校验错误 "{error}"
Then 表单提交成功，显示提示 "{message}"
Then "{field}" 字段显示默认值 "{default}"
Then 提交按钮处于禁用状态
```

---

## 列表 & 搜索

```gherkin
# 前置
Given 系统中存在 {count} 条 "{entity}" 记录
Given 系统中存在名为 "{name}" 的 "{entity}"
Given 系统中不存在任何 "{entity}" 记录

# 动作
When 用户在搜索框输入 "{keyword}"
When 用户按 "{field}" 字段筛选，值为 "{value}"
When 用户按 "{field}" 升序/降序排列
When 用户翻到第 {page} 页

# 断言
Then 列表显示 {count} 条结果
Then 列表包含名为 "{name}" 的记录
Then 列表不包含名为 "{name}" 的记录
Then 页面显示"暂无数据"提示
Then 分页组件显示共 {total} 条记录
```

---

## 增删改查（CRUD）

```gherkin
# 创建
Given 用户在创建 "{entity}" 页面
When 用户填写所有必填字段并提交
Then 新 "{entity}" 出现在列表中
Then 系统提示"创建成功"

# 读取/查看
When 用户点击 "{entity}" 的名称 "{name}"
Then 系统展示 "{entity}" 的详情页
Then 详情页显示字段 "{field}" 的值为 "{value}"

# 更新
Given 已存在名为 "{name}" 的 "{entity}"
When 用户修改 "{field}" 为 "{new_value}" 并保存
Then 列表中该条目显示更新后的值 "{new_value}"
Then 系统提示"保存成功"

# 删除
When 用户点击 "{name}" 的删除按钮
When 用户在确认弹窗中点击"确定"
Then 列表中不再显示 "{name}"
Then 系统提示"删除成功"
```

---

## API 接口

```gherkin
# 前置
Given API 服务正常运行
Given 请求头携带有效的 Bearer Token "{token}"
Given 请求体为:
  """json
  {
    "key": "value"
  }
  """

# 动作
When 客户端发送 GET 请求至 "{endpoint}"
When 客户端发送 POST 请求至 "{endpoint}"，携带请求体
When 客户端发送 PUT 请求至 "{endpoint}/{id}"
When 客户端发送 DELETE 请求至 "{endpoint}/{id}"

# 断言
Then 响应状态码为 {code}
Then 响应体包含字段 "{field}"，值为 "{value}"
Then 响应体不包含字段 "{field}"
Then 响应时间不超过 {ms} 毫秒
Then 响应头 "Content-Type" 为 "application/json"
```

---

## 状态流转

```gherkin
# 前置
Given 订单/工单/申请 "{id}" 的当前状态为 "{status}"

# 动作
When 用户执行"{action}"操作
When 系统触发自动状态变更（如支付超时）

# 断言
Then 状态变更为 "{new_status}"
Then 操作历史记录新增一条 "{action}" 日志
Then 系统向相关人员发送通知
Then 操作失败，提示 "{reason}"

# 状态流转数据驱动模板
Scenario Outline: 不同状态下的操作结果
  Given 记录状态为 <当前状态>
  When  用户执行 <操作>
  Then  系统响应为 <结果>

  Examples:
    | 当前状态 | 操作 | 结果     |
    | 待审核  | 通过 | 已通过   |
    | 待审核  | 拒绝 | 已拒绝   |
    | 已通过  | 通过 | 操作不允许 |
```

---

## 文件 & 上传

```gherkin
Given 用户准备了大小为 {size}MB 的文件 "{filename}"
Given 用户准备了格式为 "{ext}" 的文件

When 用户选择文件并点击上传
When 用户拖拽文件至上传区域

Then 文件上传成功，显示文件名 "{filename}"
Then 系统拒绝上传，提示"文件大小超出限制"
Then 系统拒绝上传，提示"不支持该文件格式"
Then 上传进度显示 100%
```

---

## 通知 & 邮件

```gherkin
Then 系统向 "{email}" 发送主题为 "{subject}" 的邮件
Then 用户收到站内通知，内容包含 "{keyword}"
Then 通知列表新增 1 条未读消息
```
