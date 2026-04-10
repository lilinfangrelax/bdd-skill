Feature: Todo 任务管理

  Scenario: 用户创建任务
    Given 用户在 TodoMVC 首页
    When 用户创建任务 "学习 pytest-bdd"
    Then 页面显示任务 "学习 pytest-bdd"

  Scenario: 用户完整操作任务
    Given API 服务正常运行
    When 客户端发送 API 请求「新增任务」
    Then API「新增任务」响应与模板匹配
    When 客户端发送 API 请求「编辑任务」
    Then API「编辑任务」响应与模板匹配
    When 客户端发送 API 请求「假删除任务」
    Then API「假删除任务」响应与模板匹配
    When 客户端发送 API 请求「永久删除任务」
    Then API「永久删除任务」响应与模板匹配

  Scenario: 用户完整操作任务（API）
    Given API 服务正常运行
    When 客户端发送 API 请求「新增任务」
    Then API「新增任务」响应与模板匹配
    When 客户端发送 API 请求「编辑任务」
    Then API「编辑任务」响应与模板匹配
    When 客户端发送 API 请求「编辑任务」
    Then API「编辑任务」响应与模板匹配
    When 客户端发送 API 请求「假删除任务」
    Then API「假删除任务」响应与模板匹配
    When 客户端发送 API 请求「永久删除任务」
    Then API「永久删除任务」响应与模板匹配
