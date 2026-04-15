"""GitHub API 冒烟场景入口。"""

from pytest_bdd import scenario


pytest_plugins = [
    "steps.api_steps",
]


@scenario("../features/github_api_smoke.feature", "查询公开仓库详情")
def test_get_public_repo_details():
    """执行公开仓库详情查询场景。"""
    pass


@scenario("../features/github_api_smoke.feature", "搜索公开仓库")
def test_search_public_repositories():
    """执行公开仓库搜索场景。"""
    pass
