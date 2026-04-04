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
        self._base_url = "https://generativelanguage.googleapis.com/v1"

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

    def generate_json(self, messages: tuple[AIMessage, ...], temperature: float) -> AIProviderResponse:
        print(f"\n[DEBUG] GeminiAIProvider: Calling {self.model}...", flush=True)

        # We'll collect the system instructions and wrap them as the FIRST user message
        # to ensure the model prioritizes the schema.
        contents = []
        system_content = ""
        user_messages = []

        for msg in messages:
            if msg.role == "system":
                system_content += f"{msg.content}\n"
            else:
                role = "model" if msg.role in ("assistant", "ai") else "user"
                user_messages.append({
                    "role": role,
                    "parts": [{"text": msg.content}]
                })

        # Inject instructions as the definitive context if they exist
        if system_content:
            contents.append({
                "role": "user",
                "parts": [{"text": f"IMPORTANT RULES:\n{system_content}\n\nSTRICT REQUIREMENT: You MUST include 'cefr_band': 'A1' and 'topic': 'romanian_basics' in your JSON output."}]
            })
            # Add an acknowledgment to "trick" the model into obedience
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood. I will provide the response in valid JSON format including all required metadata fields."}]
            })

        contents.extend(user_messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "topP": 0.8, # Slightly reduced for more deterministic output
                "maxOutputTokens": 8192,
            }
        }

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
            print(f"\n[!!!] GEMINI API ERROR {exc.code}: {details}\n", flush=True)
            if exc.code in {408, 429, 500, 503, 504}:
                raise TransientAIError(f"Gemini transient error {exc.code}: {details}") from exc
            raise AIProviderError(f"Gemini provider error {exc.code}: {details}") from exc
        except (error.URLError, TimeoutError, socket.timeout) as exc:
            print(f"\n[!!!] GEMINI NETWORK ERROR: {str(exc)}\n", flush=True)
            raise TransientAIError(f"Gemini network error: {exc}") from exc

        try:
            res_json = json.loads(response_body)
            candidate = res_json["candidates"][0]
            raw_content = candidate["content"]["parts"][0]["text"]

            message_content = self._strip_markdown(raw_content)
            # Pre-validation for debugging
            parsed = json.loads(message_content)
            if "cefr_band" not in parsed:
                print(f"[DEBUG] Model missed cefr_band. Found keys: {list(parsed.keys())}", flush=True)

            usage = res_json.get("usageMetadata", {})
            print("[DEBUG] GeminiAIProvider: Request successful.", flush=True)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            print(f"\n[!!!] GEMINI PARSING ERROR: {str(exc)}\n", flush=True)
            raise AIProviderError(f"Gemini response parsing failed: {str(exc)}") from exc

        return AIProviderResponse(
            provider_name=self.provider_name,
            model=self.model,
            content=message_content,
            finish_reason=candidate.get("finishReason"),
            prompt_tokens=usage.get("promptTokenCount"),
            completion_tokens=usage.get("candidatesTokenCount"),
        )
