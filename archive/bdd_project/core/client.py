"""HTTP 客户端封装（基础设施层）。"""

from __future__ import annotations

import requests


class HttpClient:
    """基于 requests.Session 的 API 客户端，负责 base_url 与 path 拼接。"""

    def __init__(self, base_url: str) -> None:
        self._session = requests.Session()
        self._base_url = base_url.rstrip("/")

    @property
    def base_url(self) -> str:
        """规范化后的根 URL（无尾部斜杠）。"""
        return self._base_url

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return self._base_url + path

    def get(self, path: str, **kwargs):
        return self._session.get(self._url(path), **kwargs)

    def post(self, path: str, **kwargs):
        return self._session.post(self._url(path), **kwargs)

    def put(self, path: str, **kwargs):
        return self._session.put(self._url(path), **kwargs)

    def delete(self, path: str, **kwargs):
        return self._session.delete(self._url(path), **kwargs)

    def close(self) -> None:
        """释放底层 Session。"""
        self._session.close()
