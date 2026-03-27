from __future__ import annotations

from abc import ABC, abstractmethod
import json
import socket
from typing import Any
from urllib import error, request

from app.ai.types import AIConfigurationError, AIMessage, AIProviderError, AIProviderResponse, TransientAIError


class BaseAIProvider(ABC):
    provider_name: str
    model: str

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate_json(self, messages: tuple[AIMessage, ...], temperature: float) -> AIProviderResponse:
        raise NotImplementedError


class DisabledAIProvider(BaseAIProvider):
    def __init__(self, provider_name: str = "disabled", model: str = "disabled") -> None:
        self.provider_name = provider_name
        self.model = model

    @property
    def is_configured(self) -> bool:
        return False

    def generate_json(self, messages: tuple[AIMessage, ...], temperature: float) -> AIProviderResponse:
        raise AIConfigurationError("AI provider is not configured. Set the Lumina Romana AI environment variables.")


class OpenAIChatProvider(BaseAIProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.provider_name = "openai"
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def generate_json(self, messages: tuple[AIMessage, ...], temperature: float) -> AIProviderResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url=f"{self._base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            if exc.code in {408, 409, 429, 500, 502, 503, 504}:
                raise TransientAIError(f"Transient provider error {exc.code}: {details}") from exc
            raise AIProviderError(f"Provider error {exc.code}: {details}") from exc
        except (error.URLError, TimeoutError, socket.timeout) as exc:
            raise TransientAIError(f"Transient network error: {exc}") from exc

        try:
            response_json = json.loads(response_body)
            choice = response_json["choices"][0]
            message_content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError("Provider response was missing structured chat completion data.") from exc

        content = self._normalize_content(message_content)
        usage = response_json.get("usage", {})
        return AIProviderResponse(
            provider_name=self.provider_name,
            model=response_json.get("model", self.model),
            content=content,
            response_id=response_json.get("id"),
            finish_reason=choice.get("finish_reason"),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )

    def _normalize_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
            if text_parts:
                return "".join(text_parts)
        raise AIProviderError("Provider did not return text content.")
