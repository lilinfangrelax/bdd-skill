"""响应数据提取封装。"""

from typing import Any

import jmespath


class Extractor:
    """使用 JMESPath 从响应中提取变量。"""

    @staticmethod
    def extract(data: dict, expression: str) -> Any:
        result = jmespath.search(expression, data)
        if result is None:
            raise ValueError(
                f"JMESPath 表达式 '{expression}' 在响应中未匹配到任何值。\n响应数据: {data}"
            )
        return result

    @staticmethod
    def extract_all(data: dict, expressions: dict) -> dict:
        results = {}
        errors = []
        for var_name, expr in expressions.items():
            try:
                results[var_name] = Extractor.extract(data, expr)
            except ValueError as exc:
                errors.append(str(exc))

        if errors:
            raise ValueError("变量提取失败:\n" + "\n".join(errors))

        return results

    @staticmethod
    def safe_extract(data: dict, expression: str, default=None) -> Any:
        result = jmespath.search(expression, data)
        return default if result is None else result
