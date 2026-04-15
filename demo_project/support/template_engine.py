"""Jinja2 模板渲染封装。"""

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


class TemplateEngine:
    """渲染 .j2 模板并返回 JSON 对象。"""

    def __init__(self, templates_dir: str):
        self.env = Environment(
            loader=FileSystemLoader(str(Path(templates_dir).resolve())),
            undefined=StrictUndefined,
            autoescape=False,
        )
        self.env.filters["tojson"] = json.dumps

    def render(self, template_name: str, variables: dict | None = None) -> dict:
        variables = variables or {}
        template = self.env.get_template(template_name)
        rendered_str = template.render(**variables)
        try:
            return json.loads(rendered_str)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"模板 '{template_name}' 渲染结果不是合法 JSON:\n{rendered_str}\n原始错误: {exc}"
            ) from exc

    def render_string(self, template_str: str, variables: dict | None = None) -> dict:
        variables = variables or {}
        rendered_str = self.env.from_string(template_str).render(**variables)
        return json.loads(rendered_str)
