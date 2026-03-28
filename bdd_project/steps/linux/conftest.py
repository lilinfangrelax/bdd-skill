import pytest


@pytest.fixture
def linux_app():
    """Linux 桌面应用自动化 fixture。"""
    # 后续可在此接入 dogtail、LDTP 等方案
    yield None
