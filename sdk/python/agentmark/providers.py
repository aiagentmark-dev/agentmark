"""
agentmark.providers — provider-specific LLM call implementations.

Each provider handles:
- Making the API call with with_raw_response pattern
- Extracting request_id from correct header
- Extracting generated code from response structure
- Verifying challenge echo in raw bytes
"""

from __future__ import annotations
import hashlib
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agentmark.core import CallResult


PROVIDER_CONFIG = {
    "anthropic": {
        "request_id_header": "request-id",
        "request_id_prefix": "req_01",
    },
    "openai": {
        "request_id_header": "x-request-id",
        "request_id_prefix": "req-",
    },
    "google": {
        "request_id_header": "x-goog-request-id",
        "request_id_prefix": None,  # UUID format
    },
    "mistral": {
        "request_id_header": "x-request-id",
        "request_id_prefix": None,  # UUID format
    },
    "local": {
        "request_id_header": None,
        "request_id_prefix": None,
    },
}


def get_provider(provider: str):
    providers = {
        "anthropic": AnthropicProvider(),
        "openai": OpenAIProvider(),
        "local": LocalProvider(),
    }
    if provider not in providers:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Supported: {list(providers.keys())}"
        )
    return providers[provider]


def _verify_challenge_echo(raw_bytes: bytes, challenge_token: str) -> bool:
    echo = f"agentmark-challenge-echo: {challenge_token}"
    return echo.encode() in raw_bytes


class AnthropicProvider:
    def call(self, model: str, prompt: str, challenge_token: str, **kwargs):
        try:
            import anthropic
        except ImportError:
            raise ImportError("pip install anthropic")

        from agentmark.core import CallResult

        client = anthropic.Anthropic()
        raw_response = client.messages.with_raw_response.create(
            model=model,
            max_tokens=kwargs.pop("max_tokens", 8192),
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )

        request_id = raw_response.headers.get("request-id")
        raw_bytes = raw_response.content
        response = raw_response.parse()
        code = response.content[0].text

        return CallResult(
            raw_bytes=raw_bytes,
            request_id=request_id,
            code=code,
            provider="anthropic",
            model=model,
            challenge_token=challenge_token,
            challenge_echo_verified=_verify_challenge_echo(raw_bytes, challenge_token),
        )


class OpenAIProvider:
    def call(self, model: str, prompt: str, challenge_token: str, **kwargs):
        try:
            import openai
        except ImportError:
            raise ImportError("pip install openai")

        from agentmark.core import CallResult

        client = openai.OpenAI()
        raw_response = client.chat.completions.with_raw_response.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.pop("temperature", 0),
            **kwargs,
        )

        request_id = raw_response.headers.get("x-request-id")
        raw_bytes = raw_response.content
        response = raw_response.parse()
        code = response.choices[0].message.content

        return CallResult(
            raw_bytes=raw_bytes,
            request_id=request_id,
            code=code,
            provider="openai",
            model=model,
            challenge_token=challenge_token,
            challenge_echo_verified=_verify_challenge_echo(raw_bytes, challenge_token),
        )


class LocalProvider:
    """Ollama and other local model providers."""

    def call(self, model: str, prompt: str, challenge_token: str, **kwargs):
        try:
            import requests
        except ImportError:
            raise ImportError("pip install requests")

        from agentmark.core import CallResult

        base_url = kwargs.pop("base_url", "http://localhost:11434")
        response = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()

        raw_bytes = response.content
        code = response.json().get("response", "")

        return CallResult(
            raw_bytes=raw_bytes,
            request_id=None,  # not available for local models
            code=code,
            provider="local",
            model=model,
            challenge_token=challenge_token,
            challenge_echo_verified=_verify_challenge_echo(raw_bytes, challenge_token),
        )
