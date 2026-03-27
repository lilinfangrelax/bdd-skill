Feature: Todo 任务管理

  Scenario: 用户创建任务
    Given 用户在 TodoMVC 首页
    When 用户创建任务 "学习 pytest-bdd"
    Then 页面显示任务 "学习 pytest-bdd"
