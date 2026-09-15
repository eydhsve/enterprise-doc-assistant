"""Zhipu GLM-4.7-Flash client using the OpenAI-compatible API."""

from __future__ import annotations

import logging
from typing import Any, Iterable

from .config import Settings


logger = logging.getLogger(__name__)


class LLMClientError(RuntimeError):
    """Base error for LLM operations."""


class LLMConfigurationError(LLMClientError):
    """Raised when required LLM configuration is missing."""


class LLMNetworkError(LLMClientError):
    """Raised for network and timeout errors."""


class LLMAPIError(LLMClientError):
    """Raised for API-side errors."""


class ZhipuLLMClient:
    """Small wrapper around the Zhipu OpenAI-compatible endpoint."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = settings.zhipu_model
        self._client: Any | None = None

        if self.model.lower() != "glm-4.7-flash":
            raise LLMConfigurationError(
                "本项目固定使用智谱 GLM-4.7-Flash，"
                "请将 ZHIPU_MODEL 设置为 glm-4.7-flash。"
            )

    def _get_client(self) -> Any:
        key = self.settings.zhipu_api_key.strip()
        if not key or key == "your_zhipu_api_key_here":
            raise LLMConfigurationError(
                "未配置 ZHIPU_API_KEY，请先复制 .env 并填写智谱 API Key。"
            )

        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise LLMConfigurationError(
                    "缺少 openai 依赖，请执行 "
                    "pip install -r requirements.txt。"
                ) from exc
            self._client = OpenAI(
                api_key=key,
                base_url=self.settings.zhipu_base_url,
                timeout=self.settings.llm_timeout,
                max_retries=self.settings.llm_max_retries,
            )
        return self._client

    def chat_completion(
        self,
        messages: Iterable[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Call GLM-4.7-Flash and normalize the assistant message."""

        message_list = list(messages)
        if not message_list:
            raise LLMClientError("messages 不能为空。")

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": message_list,
            "temperature": (
                self.settings.llm_temperature
                if temperature is None
                else max(0.0, min(1.0, float(temperature)))
            ),
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        try:
            from openai import (
                APIConnectionError,
                APIError,
                APIStatusError,
                APITimeoutError,
                AuthenticationError,
                RateLimitError,
            )
        except ImportError as exc:
            raise LLMConfigurationError(
                "缺少 openai 依赖，请执行 pip install -r requirements.txt。"
            ) from exc

        try:
            response = self._get_client().chat.completions.create(**kwargs)
        except AuthenticationError as exc:
            raise LLMAPIError(
                "智谱 API 鉴权失败，请检查 ZHIPU_API_KEY 是否正确。"
            ) from exc
        except RateLimitError as exc:
            raise LLMAPIError(
                "智谱 API 请求频率或额度受限，请稍后重试。"
            ) from exc
        except (APITimeoutError, APIConnectionError) as exc:
            raise LLMNetworkError(
                "无法连接智谱 API，请检查网络、代理或 base URL。"
            ) from exc
        except APIStatusError as exc:
            detail = getattr(exc, "message", str(exc))
            raise LLMAPIError(
                f"智谱 API 返回异常状态码 {exc.status_code}: {detail}"
            ) from exc
        except APIError as exc:
            raise LLMAPIError(f"智谱 API 调用失败: {exc}") from exc
        except Exception as exc:
            logger.exception("Unexpected LLM error")
            raise LLMClientError(f"大模型调用发生未预期错误: {exc}") from exc

        if not response.choices:
            raise LLMAPIError("智谱 API 未返回任何候选结果。")

        choice = response.choices[0]
        message = choice.message
        tool_calls: list[dict[str, Any]] = []
        for tool_call in getattr(message, "tool_calls", None) or []:
            function = tool_call.function
            tool_calls.append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": function.name,
                        "arguments": function.arguments or "{}",
                    },
                }
            )

        return {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": tool_calls,
            "finish_reason": choice.finish_reason,
        }

    def summarize(
        self,
        content: str,
        *,
        instruction: str = "请用中文生成结构化摘要。",
        max_chars: int = 12000,
    ) -> str:
        """Generate a summary without exposing tools to the model."""

        trimmed = content[: max(500, max_chars)]
        messages = [
            {
                "role": "system",
                "content": (
                    "你是严谨的企业文档摘要助手。只依据用户提供的原文进行概括，"
                    "不得补充原文不存在的事实。输出包含：核心结论、关键事项、"
                    "风险或待办；没有对应内容时明确写“未提及”。"
                ),
            },
            {
                "role": "user",
                "content": f"{instruction}\n\n文档内容如下：\n\n{trimmed}",
            },
        ]
        response = self.chat_completion(messages, temperature=0.1)
        return response.get("content", "").strip() or "文档未生成有效摘要。"

    def health_check(self) -> tuple[bool, str]:
        """Perform a minimal API call for status display."""

        try:
            response = self.chat_completion(
                [
                    {
                        "role": "user",
                        "content": "只回复 OK。",
                    }
                ],
                temperature=0.0,
            )
            return True, response.get("content", "").strip() or "连接成功"
        except LLMClientError as exc:
            return False, str(exc)
