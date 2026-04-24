Feature: 示例测试
    作为用户
    我希望测试示例功能
    以便验证BDD设置是否正常工作

    Scenario: 导航到GitHub
        Given 我打开浏览器
        When 我导航到 "https://github.com"
        Then 我应该看到页面标题 "GitHub"

    Scenario: 验证页面触发了目标接口请求
        Given 我打开浏览器
        When 我打开用于触发请求的测试页面
        Then 验证系统发送了指向 "httpbin.org/get" 的接口请求
