import pytest


@pytest.fixture
def terminal_session():
    """终端界面（TUI）测试会话 fixture。"""
    # 后续可在此接入 pexpect 等方案
    yield None
