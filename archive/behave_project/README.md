# behave_project 最小骨架

这个目录提供一个最小可运行的 `pytest + behave + playwright` 示例。

## 前置条件

1. 在项目根目录安装依赖：
   - `.\.venv\Scripts\python -m pip install -e .`
2. 首次使用 Playwright 时安装浏览器：
   - `.\.venv\Scripts\python -m playwright install chromium`
3. 启动本地演示服务（新终端执行）：
   - `.\.venv\Scripts\python demo/trace_click_api/server.py`

## 运行方式

- 直接运行 behave：
  - `.\.venv\Scripts\python -m behave behave_project/features`
- 通过 pytest 运行 bridge 用例：
  - `.\.venv\Scripts\python -m pytest behave_project/tests/test_behave_runner.py -v`

## 可选环境变量

- `DEMO_BASE_URL`：覆盖默认演示地址（默认 `http://127.0.0.1:8765/`）。
