import os

import pytest

from bdd_project.api.task_api import TaskApi
from bdd_project.core.client import HttpClient

# 默认与本地 mock API 一致；CI/其它环境可设置环境变量 API_BASE_URL
_DEFAULT_API_BASE = "http://localhost:8765"


def _resolve_api_base_url() -> str:
    return os.environ.get("API_BASE_URL", _DEFAULT_API_BASE).rstrip("/")


# pytest.fixture 装饰器，用于定义 pytest 的 fixture 函数，作用是：在测试运行时，自动调用该函数，并返回一个对象，这个对象可以被测试函数使用。
# 参数：
# - name: 可选，fixture 的名称，默认为函数名。
# - scope: 可选，fixture 的作用域，默认为 function，可选值为 function、class、module、session。
# - autouse: 可选，是否自动使用，默认为 False，可选值为 True、False。
# - params: 可选，参数化，默认为 None，可选值为列表或元组。
# - ids: 可选，参数化，默认为 None，可选值为列表或元组。
# - return: 可选，返回值，默认为 None，可选值为对象。

@pytest.fixture
def api_base_url() -> str:
    """API 根地址（可由环境变量 API_BASE_URL 覆盖）。"""
    return _resolve_api_base_url()


@pytest.fixture
def http_client(api_base_url: str):
    """封装 Session 与 base_url 的 HTTP 客户端。"""
    # 创建一个 HttpClient 对象，并返回给测试函数使用。
    client = HttpClient(api_base_url)
    # yield 语句用于生成一个值，这个值可以被测试函数使用。然后继续执行后续的代码，直到遇到下一个 yield 语句。在这里，yield 语句后面的代码会在测试函数执行完之后执行。
    # 通俗一点说：yield 语句后面的代码会在测试函数执行完之后执行。
    # 具体来说：
    # 1. 当测试函数执行到 yield 语句时，会暂停执行，并返回 client 对象。
    # 2. 当测试函数执行完之后，会继续执行 yield 语句后面的代码，直到遇到下一个 yield 语句。
    yield client
    # 关闭 HttpClient 对象，释放资源。
    client.close()


@pytest.fixture
def task_api(http_client: HttpClient) -> TaskApi:
    """任务 API 门面，供手写步骤注入。"""
    # 创建一个 TaskApi 对象，并返回给测试函数使用。
    return TaskApi(http_client)
