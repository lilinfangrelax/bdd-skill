# 项目规范

## Python 虚拟环境
- 安装依赖、运行 `pytest`、执行项目内脚本时，**必须使用项目根目录下的虚拟环境**（`.venv`），不要使用系统全局 Python 或其它环境。
- 依赖以 [pyproject.toml](pyproject.toml) 为准，在项目根目录执行：`pip install -e .`（勿依赖已删除的 `requirements.txt`）。
- 激活后再操作（Windows PowerShell）：`.\.venv\Scripts\Activate.ps1`
- 未激活时可直接调用解释器，例如：`.\.venv\Scripts\python -m pytest`
- 验证测试时**按单文件或单用例执行即可**，不必每次对 `bdd_project/tests` 做全量 `pytest`；示例：`.\.venv\Scripts\python -m pytest bdd_project/tests/test_web.py -v`

## Git 提交规范
- 提交信息必须使用中文
- 格式：`<类型>: <描述>`
- 常用类型：
  - `新增`: 新功能
  - `修复`: 修复 bug
  - `优化`: 代码优化/重构
  - `文档`: 文档更新
  - `测试`: 测试相关
- 使用本地配置的 git 用户信息（优先项目级，其次全局级）
- 提交信息中不添加 Co-Authored-By 等署名信息

## 代码注释规范
- 所有代码注释必须使用中文
- 包括：行内注释、块注释、文档字符串
