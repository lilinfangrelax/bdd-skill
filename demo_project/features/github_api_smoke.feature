Feature: GitHub API 冒烟测试
    作为测试人员
    我希望验证 API BDD 三层能力已接通
    以便快速检查框架可用性

    Scenario: 查询公开仓库详情
        Given 变量 "probe" 为 "framework"
        When 发送 GET 请求到 "/repos/octocat/Hello-World" 使用模板 "github/repo_probe.json.j2"
        Then 响应状态码为 200
        And 响应体字段 "full_name" 等于 "octocat/Hello-World"
        And 响应体字段 "owner.login" 不为空
        And 提取变量 "owner_login" 从响应字段 "owner.login"

    Scenario: 搜索公开仓库
        When 发送 GET 请求到 "/search/repositories" 并设置查询参数 "q" 为 "pytest-bdd"
        Then 响应状态码为 200
        And 响应体字段 "total_count" 大于 0
        And 响应体字段 "items[0].full_name" 不为空
