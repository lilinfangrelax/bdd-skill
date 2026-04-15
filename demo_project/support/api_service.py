"""API 服务编排层封装。"""

import logging
from typing import Optional

from support.extractor import Extractor
from support.http_client import HttpClient
from support.template_engine import TemplateEngine

logger = logging.getLogger(__name__)


class ApiService:
    """组合 HTTP、模板、提取能力，提供统一调用入口。"""

    def __init__(self, http_client: HttpClient, template_engine: TemplateEngine):
        self.client = http_client
        self.tpl = template_engine

    def call(
        self,
        method: str,
        path: str,
        template: Optional[str] = None,
        variables: Optional[dict] = None,
        params: Optional[dict] = None,
        extract: Optional[dict] = None,
        expected_status: Optional[int] = None,
    ) -> tuple:
        body = None
        if template:
            body = self.tpl.render(template, variables)
            logger.debug("渲染模板 '%s': %s", template, body)

        response = self.client.request(method, path, json=body, params=params)

        if expected_status is not None:
            assert response.status_code == expected_status, (
                f"期望状态码 {expected_status}，实际 {response.status_code}。\n响应体: {response.text}"
            )

        extracted = {}
        if extract and response.content:
            extracted = Extractor.extract_all(response.json(), extract)
            logger.debug("提取变量: %s", extracted)

        return response, extracted

    def get(self, path: str, **kwargs):
        return self.call("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.call("POST", path, **kwargs)

    def put(self, path: str, **kwargs):
        return self.call("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.call("DELETE", path, **kwargs)
