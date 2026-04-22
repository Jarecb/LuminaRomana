"""AI provider implementations (OpenAI/Gemini wrappers and disabled provider).

Provides BaseAIProvider abstract base class and concrete adapters that translate
application prompt packages to provider API calls and normalize responses.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import json
import re
import socket
import ssl
from typing import Any
from urllib import error, request

from app.ai.types import (
    AIConfigurationError,
    AIMessage,
    AIProviderError,
    AIProviderResponse,
    QuotaExceededAIError,
    TransientAIError,
)


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


class AIChatProvider(BaseAIProvider):
    def __init__(
            self,
            api_key: str,
            model: str,
            base_url: str,
            provider_name: str = "openai",
            timeout_seconds: float = 30.0,
    ) -> None:
        self.provider_name = provider_name
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
        except (error.URLError, TimeoutError, socket.timeout, ssl.SSLError, OSError) as exc:
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


class GeminiAIProvider(BaseAIProvider):
    def __init__(
            self,
            api_key: str,
            model: str = "gemini-2.5-flash",
            provider_name: str = "gemini",
            timeout_seconds: float = 30.0,
    ) -> None:
        self.provider_name = provider_name
        self.model = model
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _strip_markdown(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 3:
                content = parts[1]
                if content.startswith("json"):
                    content = content[4:]
                return content.strip()
        return text

    def _parse_retry_after_seconds(self, details: str) -> float | None:
        match = re.search(r'"retryDelay"\s*:\s*"(\d+)s"', details)
        if match is not None:
            return float(match.group(1))
        match = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", details, flags=re.IGNORECASE)
        if match is not None:
            return float(match.group(1))
        return None

    def generate_json(self, messages: tuple[AIMessage, ...], temperature: float) -> AIProviderResponse:
        contents = []
        system_parts = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append({"text": msg.content})
            else:
                role = "model" if msg.role in ("assistant", "ai") else "user"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.content}]
                })

        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Return valid JSON only."}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "topP": 0.8,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json",
            }
        }
        if system_parts:
            payload["system_instruction"] = {"parts": system_parts}

        body = json.dumps(payload).encode("utf-8")
        clean_model_name = self.model.replace("models/", "")
        url = f"{self._base_url}/models/{clean_model_name}:generateContent?key={self._api_key}"

        http_request = request.Request(
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429:
                raise QuotaExceededAIError(
                    f"Gemini quota exceeded {exc.code}: {details}",
                    retry_after_seconds=self._parse_retry_after_seconds(details),
                ) from exc
            if exc.code in {408, 429, 500, 503, 504}:
                raise TransientAIError(f"Gemini transient error {exc.code}: {details}") from exc
            raise AIProviderError(f"Gemini provider error {exc.code}: {details}") from exc
        except (error.URLError, TimeoutError, socket.timeout, ssl.SSLError, OSError) as exc:
            raise TransientAIError(f"Gemini network error: {exc}") from exc

        try:
            res_json = json.loads(response_body)
            candidate = res_json["candidates"][0]
            parts = candidate["content"]["parts"]
            raw_content = "".join(
                str(part.get("text", ""))
                for part in parts
                if isinstance(part, dict)
            )
            if not raw_content.strip():
                raise AIProviderError("Gemini response did not include text content.")

            message_content = self._strip_markdown(raw_content)
            usage = res_json.get("usageMetadata", {})
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError(f"Gemini response parsing failed: {str(exc)}") from exc

        return AIProviderResponse(
            provider_name=self.provider_name,
            model=self.model,
            content=message_content,
            finish_reason=candidate.get("finishReason"),
            prompt_tokens=usage.get("promptTokenCount"),
            completion_tokens=usage.get("candidatesTokenCount"),
        )
