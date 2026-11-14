"""OpenAI-compatible provider: max_output_tokens and effort reach the request body;
an endpoint that rejects one of them gets a retry without it. No network."""
import copy
from types import SimpleNamespace

import pytest

from profile_extensioner.contracts import LLMSettings
from profile_extensioner.engine.schemas import AttributionOut
from profile_extensioner.llm.base import Completion, LLMError
from profile_extensioner.llm.client import LLMClient
from profile_extensioner.llm.openai_compatible import OpenAICompatibleProvider
from profile_extensioner.store.blackboard import Store

OK = '{"verdict": "supported", "explanation": "x", "unsupported_facets": []}'


def fake_endpoint(monkeypatch, reject=None, finish_reason="stop"):
    """Record every body; answer 400 with reject(body) text when it returns one, else 200."""
    bodies = []

    def fake_post(url, headers, json, timeout):
        bodies.append(copy.deepcopy(json))
        error = reject(json) if reject else None
        if error:
            return SimpleNamespace(status_code=400, text=error, headers={})
        return SimpleNamespace(status_code=200, text="", headers={}, json=lambda: {
            "model": "m", "choices": [{"message": {"content": OK}, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2}})

    monkeypatch.setattr("profile_extensioner.llm.openai_compatible.httpx.post", fake_post)
    return bodies


def complete(provider, **settings):
    return provider.complete(system="S", user="U", schema=AttributionOut, model="m",
                             settings=LLMSettings(provider="openai-compatible", **settings))


def test_token_limit_and_effort_are_sent(monkeypatch):
    bodies = fake_endpoint(monkeypatch)
    complete(OpenAICompatibleProvider("http://x/v1"), max_output_tokens=8000, effort="low")
    assert len(bodies) == 1
    assert bodies[0]["max_tokens"] == 8000
    assert bodies[0]["reasoning_effort"] == "low"
    assert bodies[0]["response_format"]["type"] == "json_schema"


@pytest.mark.parametrize("effort,sent", [("medium", "medium"), ("high", "high"), ("xhigh", "high"), ("max", "high")])
def test_effort_maps_to_openai_levels(monkeypatch, effort, sent):
    bodies = fake_endpoint(monkeypatch)
    complete(OpenAICompatibleProvider("http://x/v1"), effort=effort)
    assert bodies[0]["reasoning_effort"] == sent


def test_rejected_reasoning_effort_is_dropped_and_remembered(monkeypatch):
    bodies = fake_endpoint(monkeypatch, lambda b: "Unsupported parameter: 'reasoning_effort' is not supported "
                                                  "with this model." if "reasoning_effort" in b else None)
    provider = OpenAICompatibleProvider("http://x/v1")
    completion = complete(provider, max_output_tokens=8000)
    assert len(bodies) == 2 and "reasoning_effort" not in bodies[1]
    assert bodies[1]["max_tokens"] == 8000 and bodies[1]["response_format"]["type"] == "json_schema"
    assert any("reasoning_effort" in note for note in completion.notes)
    complete(provider, max_output_tokens=8000)
    assert len(bodies) == 3 and "reasoning_effort" not in bodies[2]   # learned: no second round trip


def test_max_tokens_is_renamed_when_the_endpoint_asks(monkeypatch):
    bodies = fake_endpoint(monkeypatch, lambda b: "Unsupported parameter: 'max_tokens' is not supported with this "
                                                  "model. Use 'max_completion_tokens' instead." if "max_tokens" in b else None)
    complete(OpenAICompatibleProvider("http://x/v1"), max_output_tokens=8000)
    assert len(bodies) == 2
    assert "max_tokens" not in bodies[1] and bodies[1]["max_completion_tokens"] == 8000


def test_json_object_fallback_keeps_token_limit(monkeypatch):
    bodies = fake_endpoint(monkeypatch, lambda b: "unsupported" if b["response_format"]["type"] == "json_schema" else None)
    complete(OpenAICompatibleProvider("http://x/v1"), max_output_tokens=8000, effort="low")
    assert len(bodies) == 2 and bodies[1]["response_format"] == {"type": "json_object"}
    assert bodies[1]["max_tokens"] == 8000 and bodies[1]["reasoning_effort"] == "low"


def test_unexplained_400_ends_after_bounded_retries(monkeypatch):
    bodies = fake_endpoint(monkeypatch, lambda b: "bad request")
    with pytest.raises(LLMError):
        complete(OpenAICompatibleProvider("http://x/v1"), max_output_tokens=8000)
    assert 2 <= len(bodies) <= 4


def test_unexplained_400_ladder_ends_with_the_old_fallback_request(monkeypatch):
    """An endpoint that only takes what the provider sent before (json_object, no extras) still works."""
    old_shape = {"model", "messages", "response_format"}
    bodies = fake_endpoint(monkeypatch, lambda b: None if set(b) == old_shape else "bad request")
    complete(OpenAICompatibleProvider("http://x/v1"), max_output_tokens=8000)
    assert set(bodies[-1]) == old_shape and bodies[-1]["response_format"] == {"type": "json_object"}


def test_token_limit_beyond_the_context_is_dropped_but_not_remembered(monkeypatch):
    too_large = "'max_tokens' or 'max_completion_tokens' is too large: 16000. This model's maximum context length is 8192"
    calls = {"n": 0}

    def reject(body):
        calls["n"] += 1
        return too_large if calls["n"] == 1 else None

    bodies = fake_endpoint(monkeypatch, reject)
    provider = OpenAICompatibleProvider("http://x/v1")
    complete(provider, max_output_tokens=16000)
    assert len(bodies) == 2 and "max_tokens" not in bodies[1] and "max_completion_tokens" not in bodies[1]
    assert bodies[1]["response_format"]["type"] == "json_schema" and "reasoning_effort" in bodies[1]
    complete(provider, max_output_tokens=16000)
    assert bodies[2]["max_tokens"] == 16000   # prompt-dependent, so the next request keeps the limit


def test_cut_off_answer_is_an_error(monkeypatch):
    fake_endpoint(monkeypatch, finish_reason="length")
    with pytest.raises(LLMError, match="max_output_tokens"):
        complete(OpenAICompatibleProvider("http://x/v1"), max_output_tokens=50)


class SignedProvider:
    """Scripted provider whose request signature can change (as a new request dialect would)."""

    name = "openai-compatible"

    def __init__(self):
        self.signature, self.texts = "v1", ['{"verdict": "supported", "explanation": "a", "unsupported_facets": []}',
                                             '{"verdict": "supported", "explanation": "b", "unsupported_facets": []}']

    def default_model(self):
        return "m"

    def request_signature(self, settings):
        return self.signature

    def complete(self, **_):
        return Completion(text=self.texts.pop(0), model="m", stop_reason="stop", notes=["n"])

    def list_models(self):
        return ["m"]


def test_cache_does_not_replay_answers_of_another_request_dialect():
    store, provider = Store(), SignedProvider()
    llm = LLMClient(provider, LLMSettings(provider="openai-compatible"), store=store, project_id="p1")
    first, record = llm.generate(system="s", user="u", schema=AttributionOut, purpose="propose")
    assert record.stop_reason == "stop" and record.notes == ["n"]   # visible in the audit
    provider.signature = "v2"
    second, record = llm.generate(system="s", user="u", schema=AttributionOut, purpose="propose")
    assert record.cached is False and second.explanation == "b"
