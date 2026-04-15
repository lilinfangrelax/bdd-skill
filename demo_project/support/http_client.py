"""HTTP 基础封装。"""

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class HttpClient:
    """统一管理 Session、重试策略和基础请求日志。"""

    def __init__(self, base_url: str, default_headers: dict | None = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        if default_headers:
            self.session.headers.update(default_headers)

        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def set_auth_token(self, token: str, scheme: str = "Bearer"):
        """动态设置鉴权 Token。"""
        self.session.headers.update({"Authorization": f"{scheme} {token}"})

    def clear_auth(self):
        """移除鉴权头。"""
        self.session.headers.pop("Authorization", None)

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        """发送请求并记录基础日志。"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)

        logger.info("-> %s %s", method.upper(), url)
        if "json" in kwargs and kwargs["json"] is not None:
            logger.debug("Request Body: %s", kwargs["json"])

        response = self.session.request(method, url, **kwargs)

        logger.info("<- %s (%.3fs)", response.status_code, response.elapsed.total_seconds())
        logger.debug("Response Body: %s", response.text[:500])
        return response

    def get(self, path: str, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs):
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request("DELETE", path, **kwargs)
