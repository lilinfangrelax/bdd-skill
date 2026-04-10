"""任务相关 API 封装（与 fixtures/api_steps/task_api.json 路径一致）。"""

from __future__ import annotations

from typing import Any

from bdd_project.core.client import HttpClient


class TaskApi:
    """任务资源接口：仅发起请求，不做 BDD 断言。"""

    def __init__(self, client: HttpClient) -> None:
        self._client = client

    @property
    def client(self) -> HttpClient:
        return self._client

    def create_task(self, body: dict[str, Any]):
        """POST /api/tasks/create"""
        return self._client.post("/api/tasks/create", json=body)

    def list_tasks(self):
        """GET /api/tasks"""
        return self._client.get("/api/tasks")

    def update_task(self, body: dict[str, Any]):
        """POST /api/tasks/update"""
        return self._client.post("/api/tasks/update", json=body)

    def soft_delete_task(self, body: dict[str, Any]):
        """POST /api/tasks/delete（假删除）"""
        return self._client.post("/api/tasks/delete", json=body)

    def purge_task(self, body: dict[str, Any]):
        """POST /api/tasks/purge（永久删除）"""
        return self._client.post("/api/tasks/purge", json=body)
