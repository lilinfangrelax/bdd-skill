"""behave 测试运行器集成测试模块。

通过 pytest 调用 behave 命令行执行 BDD 测试，实现 pytest + behave 的桥接。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_behave_smoke():
    """冒烟测试：验证 behave 测试套件可正常执行。

    启动子进程运行 behave，检查返回码是否为 0（成功）。
    若失败则输出 stdout/stderr 便于定位问题。
    """
    repo_root = Path(__file__).resolve().parents[2]
    features_dir = repo_root / "behave_project" / "features"
    # 默认演示地址，可通过环境变量 DEMO_BASE_URL 覆盖
    env = os.environ.copy()
    env.setdefault("DEMO_BASE_URL", "http://127.0.0.1:8765/")

    # 在子进程中执行 behave 命令

    result = subprocess.run(
        [sys.executable, "-m", "behave", str(features_dir)],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )

    # 断言 behave 执行成功，失败时输出详细日志
    assert result.returncode == 0, (
        "behave 执行失败\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
    )
