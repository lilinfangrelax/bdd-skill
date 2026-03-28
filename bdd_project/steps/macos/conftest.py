import pytest


@pytest.fixture
def macos_app():
    """macOS 桌面应用自动化 fixture。"""
    # 后续可在此接入 atomacos 等自动化方案
    yield None
