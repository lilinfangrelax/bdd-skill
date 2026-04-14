Feature: 示例测试
    作为用户
    我希望测试示例功能
    以便验证BDD设置是否正常工作

    Scenario: 导航到GitHub
        Given 我打开浏览器
        When 我导航到 "https://github.com"
        Then 我应该看到页面标题 "GitHub · Change is constant. GitHub keeps you ahead. · GitHub"
