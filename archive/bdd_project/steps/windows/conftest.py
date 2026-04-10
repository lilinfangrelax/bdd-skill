import pytest


@pytest.fixture
def windows_app():
    """Windows 桌面应用自动化 fixture。"""
    # 后续可在此接入 pywinauto 等方案
    yield None
