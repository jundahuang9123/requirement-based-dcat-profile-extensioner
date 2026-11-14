"""Where the model comes from: provider selection and API keys.

Keys entered on the workbench are kept in this process's memory only. They are
never written to the blackboard, to exports or to logs, and no endpoint returns
them. Restarting the service forgets them. Environment variables are an
alternative for unattended use:

    ANTHROPIC_API_KEY        key for the ``anthropic`` provider (read by the SDK)
    RBDPE_LLM_API_KEY        key for the ``openai-compatible`` provider
    RBDPE_LLM_BASE_URL       base URL for the ``openai-compatible`` provider
    RBDPE_LLM_PROVIDER       default provider for new projects (mock | anthropic | openai-compatible)
    RBDPE_LLM_MODEL          default model for new projects
"""
from __future__ import annotations

import os
import threading
from typing import Any

from ..contracts import LLMSettings
from .base import LLMUnavailable, Provider

PROVIDERS: tuple[str, ...] = ("mock", "anthropic", "openai-compatible")


def _host(url: str | None) -> str:
    from urllib.parse import urlparse

    return (urlparse(url or "").hostname or "").lower()


class Credentials:
    """In-memory API keys, one per provider. A key for an OpenAI-compatible endpoint is bound to the host it
    was entered for, so it is never sent to another endpoint a project names."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._keys: dict[str, str] = {}
        self._hosts: dict[str, str] = {}

    def set(self, provider: str, api_key: str, base_url: str | None = None) -> None:
        if provider not in PROVIDERS:
            raise ValueError(f"unknown provider: {provider}")
        with self._lock:
            if api_key:
                self._keys[provider] = api_key
                self._hosts[provider] = _host(base_url)
            else:
                self._keys.pop(provider, None)
                self._hosts.pop(provider, None)

    def clear(self, provider: str) -> None:
        with self._lock:
            self._keys.pop(provider, None)
            self._hosts.pop(provider, None)

    def get(self, provider: str, base_url: str | None = None) -> str | None:
        """The key for ``provider`` at ``base_url``: a key bound to another host is not given out."""
        with self._lock:
            key, bound = self._keys.get(provider), self._hosts.get(provider, "")
        if key and (not bound or base_url is None or _host(base_url) == bound):
            return key
        if provider == "openai-compatible":
            env_host = _host(os.environ.get("RBDPE_LLM_BASE_URL"))
            if not env_host or base_url is None or _host(base_url) == env_host:
                return os.environ.get("RBDPE_LLM_API_KEY") or None
        return None

    def source(self, provider: str) -> str:
        """Where a key would come from: 'workbench', 'environment' or 'none'. Never the key itself."""
        with self._lock:
            if provider in self._keys:
                return "workbench"
        if provider == "anthropic" and (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            return "environment"
        if provider == "openai-compatible" and os.environ.get("RBDPE_LLM_API_KEY"):
            return "environment"
        return "none"


def default_settings() -> LLMSettings:
    provider = os.environ.get("RBDPE_LLM_PROVIDER", "mock").strip().lower() or "mock"
    if provider not in PROVIDERS:
        provider = "mock"
    return LLMSettings(
        provider=provider,  # type: ignore[arg-type]
        model=os.environ.get("RBDPE_LLM_MODEL") or None,
        base_url=os.environ.get("RBDPE_LLM_BASE_URL") or None,
    )


def build_provider(settings: LLMSettings, credentials: Credentials, **mock_options: Any) -> Provider:
    """Create the provider a project's settings ask for."""
    if settings.provider == "mock":
        from .mock import MockProvider

        return MockProvider(**mock_options)
    if settings.provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=credentials.get("anthropic"))
    if settings.provider == "openai-compatible":
        from .openai_compatible import OpenAICompatibleProvider

        base_url = settings.base_url or os.environ.get("RBDPE_LLM_BASE_URL") or ""
        return OpenAICompatibleProvider(base_url, credentials.get("openai-compatible", base_url), default_model=settings.model)
    raise LLMUnavailable(f"Unknown provider '{settings.provider}'.")


def provider_status(credentials: Credentials) -> list[dict[str, Any]]:
    """What the workbench shows in its model-provider panel (no secrets)."""
    return [
        {
            "provider": "mock",
            "label": "Offline rules (no model, no key)",
            "needs_key": False,
            "key_source": "none",
            "default_model": "rules-v1",
            "note": "Deterministic rule-based proposer for demos, tests and as a no-LLM baseline.",
        },
        {
            "provider": "anthropic",
            "label": "Anthropic (Claude)",
            "needs_key": True,
            "key_source": credentials.source("anthropic"),
            "default_model": "claude-opus-5-5",
            "note": "Official SDK; structured output; policy declines fall back to another Claude model.",
        },
        {
            "provider": "openai-compatible",
            "label": "OpenAI-compatible endpoint (OpenAI, Ollama, vLLM, gateways)",
            "needs_key": False,
            "key_source": credentials.source("openai-compatible"),
            "default_model": None,
            "note": "Needs a base URL and a model id; a key only if the endpoint asks for one.",
        },
    ]
