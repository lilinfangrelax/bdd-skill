"""BDD 项目根目录 conftest。"""

# 加载公共步骤（shared_steps 模块可为空，仅作占位）
pytest_plugins = ["bdd_project.steps.common.shared_steps"]
