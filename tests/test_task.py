from pytest_bdd import scenario

# `pytest_plugins` 是 pytest 原生支持的"插件声明"机制，专门为这种场景设计：让 pytest 去主动加载某个模块里的所有 fixture，而不需要手动 import 它们
pytest_plugins = ["tests.steps.task_steps"]


@scenario("features/task.feature", "用户创建任务")
def test_create_task():
    pass
