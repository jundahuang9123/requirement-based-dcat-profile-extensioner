"""Any endpoint that speaks the OpenAI chat-completions dialect (OpenAI, Ollama,
vLLM, LM Studio, university gateways ...). Plain HTTP, no vendor SDK.

Structured output is requested with ``response_format: json_schema``. Endpoints
that do not know it get one retry with ``json_object`` and the schema spelled
out in the system prompt; the answer is validated by ``LLMClient`` either way.

``max_output_tokens`` is sent as ``max_tokens`` and ``effort`` as
``reasoning_effort`` (xhigh/max are clamped to high). An endpoint that answers
400 naming one of them gets a retry without it (``max_tokens`` is renamed to
``max_completion_tokens`` when asked); what it rejected is remembered per model.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

import httpx
from pydantic import BaseModel

from ..contracts import LLMSettings
from .base import Completion, LLMError, LLMUnavailable, strict_json_schema

# Bump whenever the request body changes meaning, so the replay cache does not
# serve answers that were produced by a differently-shaped request.
REQUEST_DIALECT = "openai-chat/2"
# OpenAI's reasoning_effort levels; LLMSettings.effort also has Anthropic's xhigh and max.
REASONING_EFFORT = {"low": "low", "medium": "medium", "high": "high", "xhigh": "high", "max": "high"}


class OpenAICompatibleProvider:
    name = "openai-compatible"

    max_retries = 5

    def __init__(self, base_url: str, api_key: str | None = None, *, default_model: str | None = None) -> None:
        if not base_url:
            raise LLMUnavailable("An OpenAI-compatible provider needs a base URL (for example http://localhost:11434/v1).")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._default_model = default_model
        self._lock = threading.Lock()
        self._rejected: set[tuple[str, str]] = set()   # (model, feature) the endpoint answered 400 to

    def request_signature(self, settings: LLMSettings) -> str:
        """What, besides the prompts, shapes the answer: part of the replay-cache key."""
        return (f"{REQUEST_DIALECT}|max={settings.max_output_tokens}|effort={REASONING_EFFORT.get(settings.effort)}"
                f"|temperature={settings.temperature}")

    def default_model(self) -> str:
        if not self._default_model:
            raise LLMUnavailable("Choose a model for the OpenAI-compatible provider.")
        return self._default_model

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _post(self, body: dict[str, Any], timeout: float) -> httpx.Response:
        """POST with retries on rate limits (429) and server errors (5xx), honouring Retry-After."""
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.post(f"{self._base_url}/chat/completions", headers=self._headers(), json=body, timeout=timeout)
            except httpx.TimeoutException as exc:
                if attempt == self.max_retries:
                    raise LLMUnavailable(f"{self._base_url} did not answer in time: {exc}") from exc
                time.sleep(delay)
                delay = min(delay * 2, 60.0)
                continue
            except httpx.HTTPError as exc:
                raise LLMUnavailable(f"Could not reach {self._base_url}: {exc}") from exc
            if response.status_code != 429 and response.status_code < 500 or attempt == self.max_retries:
                return response
            wait = delay
            retry_after = response.headers.get("retry-after") if hasattr(response, "headers") else None
            if retry_after:
                try:
                    wait = max(wait, float(retry_after))
                except ValueError:
                    pass
            time.sleep(min(wait, 120.0))
            delay = min(delay * 2, 60.0)
        return response

    def complete(
        self,
        *,
        system: str,
        user: str,
        schema: type[BaseModel],
        model: str,
        settings: LLMSettings,
        context: dict[str, Any] | None = None,
    ) -> Completion:
        json_schema = strict_json_schema(schema)
        with self._lock:
            known = {feature for (rejected_model, feature) in self._rejected if rejected_model == model}
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": json_schema, "strict": True},
            },
            "max_tokens": settings.max_output_tokens,
        }
        effort = REASONING_EFFORT.get(settings.effort)
        if effort:
            body["reasoning_effort"] = effort
        if settings.temperature is not None:
            body["temperature"] = settings.temperature
        notes: list[str] = [f"effort {settings.effort} sent as reasoning_effort {effort}"] if effort != settings.effort else []
        for feature in sorted(known):   # what this endpoint already rejected for this model
            notes.append(f"{_degrade(body, feature, system, json_schema)} (learned earlier)")
        response = self._post(body, settings.timeout_seconds)
        tried: list[str] = []
        while response.status_code == 400:
            feature = _rejected_feature(body, response.text, tried)
            if feature is None:
                break
            tried.append(feature)
            notes.append(_degrade(body, feature, system, json_schema))
            response = self._post(body, settings.timeout_seconds)
        if tried and response.status_code < 400:
            with self._lock:   # the token limit depends on the prompt length: not remembered
                self._rejected.update((model, feature) for feature in tried if feature != "token_limit")
        if response.status_code in (401, 403):
            raise LLMUnavailable("The endpoint rejected the API key.")
        if response.status_code == 404:
            raise LLMUnavailable(f"Unknown model or endpoint ({self._base_url}, model '{model}').")
        if response.status_code == 429:
            raise LLMUnavailable("Rate limit reached; retry later.")
        if response.status_code >= 400:
            raise LLMError(f"Endpoint error {response.status_code}: {response.text[:400]}")
        try:
            data = response.json()
            choice = data["choices"][0]
            text = choice["message"].get("content") or ""
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected response shape from {self._base_url}: {response.text[:400]}") from exc
        finish_reason = str(choice.get("finish_reason") or "")
        if finish_reason == "length":
            raise LLMError(f"The answer was cut off at the output token limit ({settings.max_output_tokens}); "
                           "raise max_output_tokens.")
        usage = data.get("usage") or {}
        return Completion(
            text=_strip_code_fence(text),
            model=data.get("model") or model,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            stop_reason=finish_reason,
            notes=notes,
        )

    def list_models(self) -> list[str]:
        try:
            response = httpx.get(f"{self._base_url}/models", headers=self._headers(), timeout=20.0)
            response.raise_for_status()
            return sorted(item["id"] for item in response.json().get("data", []) if "id" in item)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise LLMUnavailable(f"Could not list models at {self._base_url}: {exc}") from exc


def _rejected_feature(body: dict[str, Any], error_text: str, tried: list[str]) -> str | None:
    """Which optional part of ``body`` to give up after a 400: the one the error names first, else
    json_schema (the long-standing fallback), then reasoning_effort, then the token limit, so the
    last attempt is the request this provider sent before it knew these parameters. Each at most once."""
    text = (error_text or "").lower()
    has_limit = "max_tokens" in body or "max_completion_tokens" in body
    candidates = []
    if "reasoning_effort" in body and ("reasoning" in text or "think" in text):
        candidates.append("reasoning_effort")
    if "max_tokens" in body and "max_tokens" in text and "max_completion_tokens" in text and "too large" not in text:
        candidates.append("max_tokens")        # e.g. OpenAI reasoning models: "use max_completion_tokens"
    if has_limit and ("max_tokens" in text or "max_completion_tokens" in text or "context length" in text):
        candidates.append("token_limit")       # limit beyond the model's context: the server's own limit is lower
    if body["response_format"].get("type") == "json_schema":
        candidates.append("json_schema")
    if "reasoning_effort" in body:
        candidates.append("reasoning_effort")
    if has_limit:
        candidates.append("token_limit")
    return next((feature for feature in candidates if feature not in tried), None)


def _degrade(body: dict[str, Any], feature: str, system: str, json_schema: dict[str, Any]) -> str:
    """Change ``body`` so that it no longer uses ``feature``; return a note for the audit record."""
    if feature == "reasoning_effort":
        body.pop("reasoning_effort", None)
        return "reasoning_effort rejected; retried without it"
    if feature == "max_tokens":
        body["max_completion_tokens"] = body.pop("max_tokens")
        return "max_tokens rejected; retried with max_completion_tokens"
    if feature == "token_limit":
        limit = body.pop("max_tokens", None) or body.pop("max_completion_tokens", None)
        return f"output token limit {limit} rejected; retried with the endpoint's own limit"
    # json_schema: fall back to json_object + schema in the prompt.
    body["response_format"] = {"type": "json_object"}
    body["messages"][0]["content"] = (
        f"{system}\n\nAnswer with one JSON object that validates against this JSON Schema:\n{json.dumps(json_schema)}"
    )
    return "json_schema response format rejected; retried with json_object"


def _strip_code_fence(text: str) -> str:
    """Some local models wrap JSON in a Markdown fence even when asked not to."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    return stripped.strip()
