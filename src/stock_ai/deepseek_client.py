from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from stock_ai.exceptions import AIAnalysisError


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"

Transport = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


def _default_transport(
    endpoint: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        try:
            detail = error.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(error)
        if len(detail) > 800:
            detail = detail[:800] + "..."
        raise AIAnalysisError(
            f"DeepSeek接口返回HTTP {error.code}：{detail}"
        ) from error
    except (URLError, TimeoutError) as error:
        raise AIAnalysisError(f"无法连接DeepSeek接口：{error}") from error

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as error:
        raise AIAnalysisError("DeepSeek接口没有返回有效JSON响应。") from error
    if not isinstance(result, dict):
        raise AIAnalysisError("DeepSeek接口响应格式不正确。")
    return result


def _parse_model_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise AIAnalysisError("模型没有返回可解析的分析JSON。")
        try:
            result = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as error:
            raise AIAnalysisError("模型返回的分析JSON格式不完整。") from error
    if not isinstance(result, dict):
        raise AIAnalysisError("模型返回的分析结果不是JSON对象。")
    return result


class DeepSeekClient:
    """Minimal OpenAI-compatible DeepSeek client using the standard library."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120,
        transport: Transport | None = None,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = (
            base_url
            or os.getenv("DEEPSEEK_BASE_URL")
            or DEFAULT_BASE_URL
        ).rstrip("/")
        self.model = model or os.getenv("DEEPSEEK_MODEL") or DEFAULT_MODEL
        self.timeout = timeout
        self.transport = transport or _default_transport

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    def generate_analysis(
        self,
        messages: list[dict[str, str]],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.api_key:
            raise AIAnalysisError(
                "缺少DEEPSEEK_API_KEY。请先在PowerShell设置："
                '$env:DEEPSEEK_API_KEY="你的API密钥"'
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 6000,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "stock-ai-research-assistant/0.2.0",
        }
        response = self.transport(
            self.endpoint,
            payload,
            headers,
            self.timeout,
        )
        try:
            message = response["choices"][0]["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError) as error:
            api_error = response.get("error")
            if api_error:
                raise AIAnalysisError(f"DeepSeek接口错误：{api_error}") from error
            raise AIAnalysisError("DeepSeek响应中缺少模型输出内容。") from error
        if not isinstance(content, str) or not content.strip():
            raise AIAnalysisError("DeepSeek返回了空的分析内容。")

        report = _parse_model_json(content)
        usage = response.get("usage", {})
        return report, usage if isinstance(usage, dict) else {}
