"""Provider adapters for the free-API edition of AI Review Lab."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from typing import Any

import requests


def _safe_excerpt(value: Any, limit: int = 1200) -> str:
    """Return a bounded error excerpt without ever including request headers."""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    text = str(value or "")
    for env_name in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
        secret = os.getenv(env_name, "").strip()
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text[:limit] + ("…" if len(text) > limit else "")


@dataclass
class ProviderError(Exception):
    provider: str
    message: str
    status_code: int | None = None
    error_type: str = "provider_error"
    hint: str = ""
    request_id: str = ""
    response_excerpt: str = ""

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderConfig:
    key: str
    model: str
    enabled: bool


def env_flag(name: str, default: bool = True) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class BaseProvider:
    name = "base"
    label = "Base"
    key_env = ""
    model_env = ""
    default_model = ""
    enable_env = ""

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.config = ProviderConfig(
            key=os.getenv(self.key_env, "").strip(),
            model=os.getenv(self.model_env, self.default_model).strip() or self.default_model,
            enabled=env_flag(self.enable_env),
        )
        self.timeout = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "90"))
        self.max_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "1800"))

    @property
    def ready(self) -> bool:
        return self.config.enabled and bool(self.config.key)

    def public_status(self) -> dict[str, Any]:
        return {
            "id": self.name,
            "label": self.label,
            "enabled": self.config.enabled,
            "configured": bool(self.config.key),
            "ready": self.ready,
            "model": self.config.model,
        }

    def _ensure_ready(self) -> None:
        if not self.config.enabled:
            raise ProviderError(self.name, "환경 설정에서 비활성화된 공급자입니다.", error_type="disabled")
        if not self.config.key:
            raise ProviderError(
                self.name,
                f"{self.key_env}가 설정되지 않았습니다.",
                error_type="missing_api_key",
                hint=".env.example을 .env로 복사한 뒤 이 공급자의 API 키를 입력하세요.",
            )

    def _raise_http_error(self, response: requests.Response) -> None:
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        message = "공급자가 요청을 거부했습니다."
        error_type = "http_error"
        if isinstance(body, dict):
            error = body.get("error", body)
            if isinstance(error, dict):
                message = str(error.get("message") or message)
                error_type = str(error.get("type") or error.get("status") or error_type)
            elif error:
                message = str(error)
        hint = {
            400: "모델명과 요청 크기를 확인하세요.",
            401: "API 키가 올바른지 확인하세요.",
            403: "API 키 권한 또는 프로젝트 제한을 확인하세요.",
            404: "모델명이 현재 계정에서 사용 가능한지 확인하세요.",
            429: "무료 한도 또는 속도 제한에 도달했습니다. 잠시 후 다시 시도하세요.",
        }.get(response.status_code, "공급자 상태와 네트워크 연결을 확인하세요.")
        raise ProviderError(
            self.name,
            _safe_excerpt(message, 600),
            status_code=response.status_code,
            error_type=error_type,
            hint=hint,
            request_id=response.headers.get("x-request-id", response.headers.get("request-id", "")),
            response_excerpt=_safe_excerpt(body),
        )

    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class GeminiProvider(BaseProvider):
    name = "gemini"
    label = "Google Gemini"
    key_env = "GEMINI_API_KEY"
    model_env = "GEMINI_MODEL"
    default_model = "gemini-2.5-flash-lite"
    enable_env = "ENABLE_GEMINI"

    def generate(self, prompt: str) -> str:
        self._ensure_ready()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.model}:generateContent"
        try:
            response = self.session.post(
                url,
                headers={"x-goog-api-key": self.config.key, "Content-Type": "application/json"},
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": self.max_tokens, "temperature": 0.35},
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ProviderError(self.name, str(exc), error_type="network_error", hint="인터넷 연결과 방화벽을 확인하세요.") from exc
        if not response.ok:
            self._raise_http_error(response)
        try:
            candidates = response.json()["candidates"]
            text = "\n".join(part.get("text", "") for part in candidates[0]["content"]["parts"]).strip()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(self.name, "응답에서 텍스트를 찾지 못했습니다.", error_type="invalid_response", response_excerpt=_safe_excerpt(response.text)) from exc
        if not text:
            raise ProviderError(self.name, "빈 응답을 받았습니다.", error_type="empty_response")
        return text


class OpenAICompatibleProvider(BaseProvider):
    api_url = ""

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.config.key}", "Content-Type": "application/json"}

    def generate(self, prompt: str) -> str:
        self._ensure_ready()
        try:
            response = self.session.post(
                self.api_url,
                headers=self.headers(),
                json={
                    "model": self.config.model,
                    "messages": [
                        {"role": "system", "content": "사실과 추론을 구분하는 신중한 전문 분석가로 답하세요."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": 0.35,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ProviderError(self.name, str(exc), error_type="network_error", hint="인터넷 연결과 방화벽을 확인하세요.") from exc
        if not response.ok:
            self._raise_http_error(response)
        try:
            text = response.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            raise ProviderError(self.name, "응답에서 텍스트를 찾지 못했습니다.", error_type="invalid_response", response_excerpt=_safe_excerpt(response.text)) from exc
        if not text:
            raise ProviderError(self.name, "빈 응답을 받았습니다.", error_type="empty_response")
        return text


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    label = "Groq"
    key_env = "GROQ_API_KEY"
    model_env = "GROQ_MODEL"
    default_model = "llama-3.1-8b-instant"
    enable_env = "ENABLE_GROQ"
    api_url = "https://api.groq.com/openai/v1/chat/completions"


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    label = "OpenRouter Free"
    key_env = "OPENROUTER_API_KEY"
    model_env = "OPENROUTER_MODEL"
    default_model = "openrouter/free"
    enable_env = "ENABLE_OPENROUTER"
    api_url = "https://openrouter.ai/api/v1/chat/completions"

    def headers(self) -> dict[str, str]:
        headers = super().headers()
        site_url = os.getenv("OPENROUTER_SITE_URL", "").strip()
        app_name = os.getenv("OPENROUTER_APP_NAME", "AI Review Lab Free").strip()
        if site_url:
            headers["HTTP-Referer"] = site_url
        if app_name:
            headers["X-Title"] = app_name
        return headers


def build_providers(session: requests.Session | None = None) -> dict[str, BaseProvider]:
    providers = [GeminiProvider(session), GroqProvider(session), OpenRouterProvider(session)]
    return {provider.name: provider for provider in providers}
